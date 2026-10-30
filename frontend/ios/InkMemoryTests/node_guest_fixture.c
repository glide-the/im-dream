// [Input] Private qualification root and actual Node-created pipe descriptors.
// [Output] Arbitrary original guest argv execution with startup/exit/signal metadata.
// [Pos] Temporary app-hosted fixture; production process and permission boundaries retained.
// [Sync] 2026-10-25: isolate each invocation's signals and proc access with a fork-inherited generation.
#include "node_guest_fixture.h"
#include <pthread.h>
#include <signal.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include "kernel/calls.h"
#include "kernel/init.h"
#include "kernel/task.h"
#include "kernel/signal.h"
#include "fs/path.h"
#include "fs/real.h"
#include "fs/proc.h"

struct invocation {
    struct invocation *next;
    char *file, *argv, *environment, *cwd;
    int argc, fd[3], pid, startup, started, finished, references;
    uint32_t scope_id;
    InkGuestExitCallback callback;
    void *context;
};
static pthread_mutex_t state_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t state_changed = PTHREAD_COND_INITIALIZER;
static struct invocation *invocations;
static int kernel_state;
static char *kernel_root;
static struct sigaction original_usr1;
extern void sigusr1_handler(int);
extern int do_wait(int, pid_t_, struct siginfo_ *, struct rusage_ *, int);

// These immutable records remain owned by this qualification kernel until App exit.
// Their lifetime covers fork descendants that outlive the original invocation.
// Production use requires complete filesystem/process ownership and scope reclamation.
struct execution_scope {
    struct execution_scope *next;
    uint32_t id;
    uint16_t http_port, socks_port;
    struct InkGuestFilesystemRules filesystem;
};
static pthread_mutex_t scope_lock = PTHREAD_MUTEX_INITIALIZER;
static struct execution_scope *execution_scopes;
static uint32_t next_scope = 1;
extern syscall_t syscall_table[];
extern const struct fd_ops socket_fdops;
static syscall_t original_socket, original_sendto;
static struct fs_ops scoped_procfs;
static struct fd_ops scoped_procfd;
extern const struct fd_ops procfs_fdops;

uint32_t InkNodeGuestExecutionScope(uint16_t http_proxy_port, uint16_t socks_proxy_port,
        const struct InkGuestFilesystemRules *filesystem) {
    struct execution_scope *scope = calloc(1, sizeof(*scope));
    if (!scope) return 0;
    if (InkNodeGuestCopyFilesystemRules(&scope->filesystem, filesystem) < 0) {free(scope); return 0;}
    pthread_mutex_lock(&scope_lock);
    if (!next_scope) {
        pthread_mutex_unlock(&scope_lock);
        InkNodeGuestFreeFilesystemRules(&scope->filesystem);
        free(scope);
        return 0;
    }
    scope->id = next_scope++;
    scope->http_port = http_proxy_port;
    scope->socks_port = socks_proxy_port;
    scope->next = execution_scopes;
    execution_scopes = scope;
    pthread_mutex_unlock(&scope_lock);
    return scope->id;
}

static int find_execution_scope(uint64_t id, struct execution_scope *copy) {
    int found = 0;
    pthread_mutex_lock(&scope_lock);
    for (const struct execution_scope *scope = execution_scopes; scope; scope = scope->next) {
        if (scope->id != id) continue;
        if (copy) *copy = *scope;
        found = 1;
        break;
    }
    pthread_mutex_unlock(&scope_lock);
    return found;
}

static uint32_t new_invocation_scope(uint32_t template_id) {
    struct execution_scope source;
    if (!find_execution_scope(template_id,&source)) return 0;
    struct execution_scope *scope=malloc(sizeof(*scope));
    if(!scope)return 0;
    *scope=source; // Immutable arrays remain owned by the kernel's retained template.
    pthread_mutex_lock(&scope_lock);
    if(!next_scope){pthread_mutex_unlock(&scope_lock);free(scope);return 0;}
    scope->id=next_scope++;scope->next=execution_scopes;execution_scopes=scope;
    pthread_mutex_unlock(&scope_lock);return scope->id;
}

// Called by the qualified proc core while pids_lock is held, before exposing a task.
int InkNodeGuestTaskAccessAllowed(struct task *task) {
    return current && current->group && current->group->fs_context && task &&
        task->pid>1 && !task->exiting && task->group &&
        task->group->fs_context==current->group->fs_context;
}

static int signal_task(struct task *task,int signal,uint32_t scope,int guest) {
    if(!task || !task->group || task->pid<=1 || task->group->fs_context!=scope)return _EPERM;
    if(guest && !superuser() && current->uid!=task->uid && current->uid!=task->suid &&
        current->euid!=task->uid && current->euid!=task->suid)return _EPERM;
    struct siginfo_ info=SIGINFO_NIL;
    if(guest){info.code=SI_USER_;info.kill.pid=current->pid;info.kill.uid=current->uid;}
    send_signal(task,signal,info);return 0;
}

static int scoped_signal(int32_t pid,int signal,uint32_t scope,int guest,int32_t tgid) {
    if((unsigned)signal>=NUM_SIGS)return _EINVAL;
    if(!scope)return guest?_EPERM:_ESRCH;
    if(!pid){if(!guest)return _EINVAL;pid=-current->group->pgid;}
    int result=_ESRCH;
    lock(&pids_lock);
    if(pid>0) {
        struct task *target=pid_get_task(pid);
        if(target && (!tgid || target->tgid==tgid)) {
            if(!guest && (target->exiting || target->zombie || !target->group || target->group->fs_context!=scope))result=_ESRCH;
            else result=signal_task(target,signal,scope,guest);
        }
    } else {
        int found=0;
        for(int id=2;id<MAX_PID;id++) {
            struct task *task=pid_get_task(id);
            if(!task || !task->group || !task_is_leader(task))continue;
            if(!guest && (task->exiting || task->zombie))continue;
            if(pid==-1 ? task==current : task->group->pgid!=(uint64_t)-(int64_t)pid)continue;
            found=1;
            if(task->group->fs_context!=scope)continue;
            int error=signal_task(task,signal,scope,guest);
            if(!error)result=0;else if(result!=0)result=error;
        }
        if(!found && guest && pid!=-1)result=_EPERM;
    }
    unlock(&pids_lock);return result;
}

static int64_t guest_kill(uint64_t pid,uint64_t signal,uint64_t c,uint64_t d,uint64_t e,uint64_t f) {
    (void)c;(void)d;(void)e;(void)f;
    uint32_t scope=current&&current->group?current->group->fs_context:0;
    return scoped_signal((int32_t)pid,(dword_t)signal,scope,1,0);
}
static int64_t guest_tkill(uint64_t tid,uint64_t signal,uint64_t c,uint64_t d,uint64_t e,uint64_t f) {
    if((int32_t)tid<=0)return _EINVAL;
    return guest_kill(tid,signal,c,d,e,f);
}
static int64_t guest_tgkill(uint64_t tgid,uint64_t tid,uint64_t signal,uint64_t d,uint64_t e,uint64_t f) {
    (void)d;(void)e;(void)f;
    if((int32_t)tgid<=0 || (int32_t)tid<=0)return _EINVAL;
    return scoped_signal((int32_t)tid,(dword_t)signal,current->group->fs_context,1,(int32_t)tgid);
}

static uint32_t current_scope_id(void) {return current&&current->group?current->group->fs_context:0;}
static int proc_access(const char *path,int writing) {
    while(*path=='/')path++;
    if(!strncmp(path,"ish",3) && (!path[3] || path[3]=='/'))return _EACCES;
    char full[MAX_PATH];int length=snprintf(full,sizeof(full),"/proc%s%s",*path?"/":"",path);
    if(length<0 || length>=MAX_PATH || InkNodeGuestFilesystemPathAllowed(current_scope_id(),full,writing)<0)return _EACCES;
    if(*path>='0' && *path<='9') {
        char *end;unsigned long pid=strtoul(path,&end,10);
        if((*end && *end!='/') || !pid || pid>=MAX_PID)return _EACCES;
        lock(&pids_lock);int permit=InkNodeGuestTaskAccessAllowed(pid_get_task(pid));unlock(&pids_lock);
        if(!permit)return _EACCES;
    } else if(writing)return _EACCES;
    return 0;
}
static int proc_descriptor_access(struct fd *fd,int writing) {
    if((uintptr_t)fd->data!=current_scope_id())return _EACCES;
    char path[MAX_PATH];int result=procfs.getpath(fd,path);
    return result<0?result:proc_access(path,writing);
}
static struct fd *scoped_proc_open(struct mount *mount,const char *path,int flags,int mode) {
    int result=proc_access(path,(flags&(O_WRONLY_|O_RDWR_))!=0);
    if(result<0)return ERR_PTR(result);
    struct fd *fd=procfs.open(mount,path,flags,mode);
    if(!IS_ERR(fd)){fd->data=(void*)(uintptr_t)current_scope_id();fd->ops=&scoped_procfd;}
    return fd;
}
static int scoped_proc_stat(struct mount *mount,const char *path,struct statbuf *stat) {
    int result=proc_access(path,0);return result<0?result:procfs.stat(mount,path,stat);
}
static int scoped_proc_fstat(struct fd *fd,struct statbuf *stat) {
    int result=proc_descriptor_access(fd,0);return result<0?result:procfs.fstat(fd,stat);
}
static int scoped_proc_getpath(struct fd *fd,char *path) {
    int result=proc_descriptor_access(fd,0);return result<0?result:procfs.getpath(fd,path);
}
static int scoped_proc_unlink(struct mount *mount,const char *path) {
    int result=proc_access(path,1);return result<0?result:procfs.unlink(mount,path);
}
static ssize_t scoped_proc_readlink(struct mount *mount,const char *path,char *buffer,size_t length) {
    int result=proc_access(path,0);return result<0?result:procfs.readlink(mount,path,buffer,length);
}
static ssize_t scoped_proc_pread(struct fd *fd,void *buffer,size_t length,off_t offset) {
    int result=proc_descriptor_access(fd,0);return result<0?result:procfs_fdops.pread(fd,buffer,length,offset);
}
static ssize_t scoped_proc_pwrite(struct fd *fd,const void *buffer,size_t length,off_t offset) {
    int result=proc_descriptor_access(fd,1);return result<0?result:procfs_fdops.pwrite(fd,buffer,length,offset);
}
static off_t_ scoped_proc_lseek(struct fd *fd,off_t_ offset,int whence) {
    int result=proc_descriptor_access(fd,0);return result<0?result:procfs_fdops.lseek(fd,offset,whence);
}
static int scoped_proc_readdir(struct fd *fd,struct dir_entry *entry) {
    int result=proc_descriptor_access(fd,0);if(result<0)return result;
    char path[MAX_PATH];result=procfs.getpath(fd,path);if(result<0)return result;
    while((result=procfs_fdops.readdir(fd,entry))>0) {
        char candidate[MAX_PATH];int length=snprintf(candidate,sizeof(candidate),"%s/%s",path,entry->name);
        if(length>=0 && length<MAX_PATH && !proc_access(candidate,0))return result;
    }
    return result;
}

const struct InkGuestFilesystemRules *InkNodeGuestFilesystemRulesForScope(uint32_t id) {
    const struct InkGuestFilesystemRules *result = NULL;
    pthread_mutex_lock(&scope_lock);
    for (const struct execution_scope *scope = execution_scopes; scope; scope = scope->next)
        if (scope->id == id) {result = &scope->filesystem; break;}
    pthread_mutex_unlock(&scope_lock);
    return result;
}

int InkNodeGuestCheckInheritedFD(uint32_t scope, int fd, int writing) {
    return kernel_root ? InkNodeGuestInheritedFileAllowed(kernel_root, scope, fd, writing) : _EACCES;
}

static struct execution_scope current_execution_scope(void) {
    struct execution_scope scope = {};
    if (current && current->group)
        find_execution_scope(current->group->fs_context, &scope);
    return scope;
}

static int64_t deny_guest_operation(uint64_t a, uint64_t b, uint64_t c,
        uint64_t d, uint64_t e, uint64_t f) {
    (void)a; (void)b; (void)c; (void)d; (void)e; (void)f;
    return _EPERM;
}

static int64_t scoped_socket(uint64_t domain, uint64_t type, uint64_t protocol,
        uint64_t d, uint64_t e, uint64_t f) {
    struct execution_scope scope = current_execution_scope();
    if ((!scope.http_port && !scope.socks_port) ||
        (domain != AF_INET_ && domain != AF_INET6_) ||
        (type & 0xf) != SOCK_STREAM_ || (protocol != 0 && protocol != IPPROTO_TCP))
        return _EACCES;
    return original_socket(domain, type, protocol, d, e, f);
}

static int64_t scoped_connect(uint64_t number, uint64_t address, uint64_t length,
        uint64_t d, uint64_t e, uint64_t f) {
    (void)d; (void)e; (void)f;
    struct execution_scope scope = current_execution_scope();
    if (!scope.http_port && !scope.socks_port) return _EACCES;
    if (length < 2 || length > sizeof(struct sockaddr_max_)) return _EINVAL;
    unsigned char guest[sizeof(struct sockaddr_max_)] = {};
    if (user_read(address, guest, length)) return _EFAULT;
    uint16_t family, port;
    memcpy(&family, guest, sizeof(family));
    if (length < 4) return _EINVAL;
    memcpy(&port, guest + 2, sizeof(port));
    port = ntohs(port);
    if (!port || (port != scope.http_port && port != scope.socks_port)) return _EACCES;
    struct sockaddr_storage native = {};
    socklen_t native_size;
    if (family == AF_INET_) {
        if (length < 16) return _EINVAL;
        const unsigned char loopback[] = {127, 0, 0, 1};
        if (memcmp(guest + 4, loopback, sizeof(loopback))) return _EACCES;
        struct sockaddr_in *ipv4 = (void *)&native;
        ipv4->sin_len = sizeof(*ipv4); ipv4->sin_family = AF_INET;
        ipv4->sin_port = htons(port);
        memcpy(&ipv4->sin_addr, loopback, sizeof(loopback));
        native_size = sizeof(*ipv4);
    } else if (family == AF_INET6_) {
        if (length < 28) return _EINVAL;
        static const unsigned char loopback[16] = {[15] = 1};
        uint32_t scope_id;
        memcpy(&scope_id, guest + 24, sizeof(scope_id));
        if (scope_id || memcmp(guest + 8, loopback, sizeof(loopback))) return _EACCES;
        struct sockaddr_in6 *ipv6 = (void *)&native;
        ipv6->sin6_len = sizeof(*ipv6); ipv6->sin6_family = AF_INET6;
        ipv6->sin6_port = htons(port);
        memcpy(&ipv6->sin6_addr, loopback, sizeof(loopback));
        native_size = sizeof(*ipv6);
    } else return _EACCES;
    struct fd *socket = f_get_retained((fd_t)number);
    if (!socket) return _EBADF;
    int result;
    if (socket->ops != &socket_fdops) result = _ENOTSOCK;
    else if (socket->socket.domain != family || socket->socket.type != SOCK_STREAM_)
        result = _EACCES;
    else {
        // Use the validated copy, never re-read mutable guest sockaddr memory.
        result = connect(socket->real_fd, (const void *)&native, native_size);
        if (result < 0) result = errno_map();
    }
    fd_close(socket);
    return result;
}

static int64_t scoped_sendto(uint64_t fd, uint64_t buffer, uint64_t length,
        uint64_t flags, uint64_t destination, uint64_t address_length) {
    if (destination || address_length) return _EACCES;
    return original_sendto(fd, buffer, length, flags, destination, address_length);
}

static void install_network_boundary(void) {
    // Fixed Linux arm64 ABI slots from the pinned kernel/arch/arm64/calls.c.
    original_socket = syscall_table[198];
    original_sendto = syscall_table[206];
    syscall_table[198] = scoped_socket;
    syscall_table[203] = scoped_connect;
    syscall_table[206] = scoped_sendto;
    syscall_table[129]=guest_kill;syscall_table[130]=guest_tkill;syscall_table[131]=guest_tgkill;
    scoped_procfs=procfs;scoped_procfd=procfs_fdops;
    scoped_procfs.open=scoped_proc_open;scoped_procfs.stat=scoped_proc_stat;
    scoped_procfs.fstat=scoped_proc_fstat;scoped_procfs.readlink=scoped_proc_readlink;
    scoped_procfs.getpath=scoped_proc_getpath;scoped_procfs.unlink=scoped_proc_unlink;
    scoped_procfd.pread=scoped_proc_pread;scoped_procfd.pwrite=scoped_proc_pwrite;
    scoped_procfd.readdir=scoped_proc_readdir;scoped_procfd.lseek=scoped_proc_lseek;
    // Named Unix sockets, local listeners and ancillary message APIs await qualification.
    const unsigned denied[] = {39, 40, 41, 51, 97, 200, 201, 202, 211, 212, 242, 243, 268, 269};
    for (size_t n = 0; n < sizeof(denied) / sizeof(*denied); n++)
        syscall_table[denied[n]] = deny_guest_operation;
}

static void guest_signal(int number, siginfo_t *info, void *context) {
    if (current) {
        sigusr1_handler(number);
        return;
    }
    if (original_usr1.sa_handler == SIG_IGN) return;
    if (original_usr1.sa_handler == SIG_DFL) {
        sigaction(number, &original_usr1, NULL);
        raise(number);
        return;
    }
    if (original_usr1.sa_flags & SA_SIGINFO)
        original_usr1.sa_sigaction(number, info, context);
    else original_usr1.sa_handler(number);
}

static void release_invocation(struct invocation *call) {
    pthread_mutex_lock(&state_lock);
    int last = --call->references == 0;
    pthread_mutex_unlock(&state_lock);
    if (last) {
        free(call->file); free(call->argv); free(call->environment); free(call->cwd);
        free(call);
    }
}

static void guest_exit(struct task *task, int status) {
    pthread_mutex_lock(&state_lock);
    struct invocation **position = &invocations;
    while (*position && (*position)->pid != task->pid) position = &(*position)->next;
    struct invocation *call = *position;
    if (call) {
        *position = call->next;
        call->finished = 1;
        // This callback queues an async notification; it never enters JavaScript here.
        call->callback(call->context, status);
        pthread_cond_broadcast(&state_changed);
    }
    pthread_mutex_unlock(&state_lock);
    if (call) release_invocation(call);
}

static void block_host_pipe_signal(void) {
    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGPIPE);
    pthread_sigmask(SIG_BLOCK, &mask, NULL);
}

static void *initialize_kernel(void *unused) {
    (void)unused;
    block_host_pipe_signal();
    struct sigaction old_pipe;
    sigaction(SIGUSR1, NULL, &original_usr1);
    sigaction(SIGPIPE, NULL, &old_pipe);
    int result = mount_root(InkNodeGuestFilesystem(), kernel_root);
    if (!result) result = become_first_process();
    if (!result) install_network_boundary();
    // Preserve the application's original signal behavior on all non-guest threads.
    sigaction(SIGPIPE, &old_pipe, NULL);
    struct sigaction chained = {.sa_sigaction=guest_signal, .sa_flags=SA_SIGINFO};
    sigemptyset(&chained.sa_mask);
    sigaddset(&chained.sa_mask, SIGUSR1);
    if (!result) sigaction(SIGUSR1, &chained, NULL);
    if (!result) {
        current->thread = pthread_self();
        result = do_mount(&scoped_procfs, "proc", "/proc", "", 0);
    }
    if (!result) result = do_mount(&devptsfs, "devpts", "/dev/pts", "", 0);
    if (!result) exit_hook = guest_exit;
    pthread_mutex_lock(&state_lock);
    kernel_state = result ? result : 2;
    pthread_cond_broadcast(&state_changed);
    pthread_mutex_unlock(&state_lock);
    if (result) return NULL;
    // Keep guest PID 1 alive and reap children; executing/exiting PID 1 would halt the app.
    for (;;) {
        struct siginfo_ info = {};
        int wait_result = do_wait(0, 0, &info, NULL, (1 << 0) | (1 << 2));
        if (wait_result >= 0 && info.child.pid) continue;
        usleep(10000);
    }
}

int InkNodeGuestInitialize(const char *root) {
    pthread_mutex_lock(&state_lock);
    if (!kernel_state) {
        kernel_root = strdup(root);
        kernel_state = 1;
        pthread_t thread;
        int error = pthread_create(&thread, NULL, initialize_kernel, NULL);
        if (error) kernel_state = -error;
        else pthread_detach(thread);
    }
    while (kernel_state == 1) pthread_cond_wait(&state_changed, &state_lock);
    int result = kernel_state == 2 ? (strcmp(root, kernel_root) ? _EINVAL : 0) : kernel_state;
    pthread_mutex_unlock(&state_lock);
    return result;
}

static void startup_ready(struct invocation *call, int result) {
    pthread_mutex_lock(&state_lock);
    call->startup = result;
    call->started = 1;
    pthread_cond_broadcast(&state_changed);
    pthread_mutex_unlock(&state_lock);
}

static int execute_guest_file(struct invocation *call) {
    if (strchr(call->file, '/'))
        return do_execve(call->file, call->argc, call->argv, call->environment);
    const char *path = "/usr/bin:/bin";
    for (const char *entry = call->environment; *entry; entry += strlen(entry) + 1)
        if (!strncmp(entry, "PATH=", 5)) { path = entry + 5; break; }
    int denied = 0;
    for (;;) {
        const char *separator = strchr(path, ':');
        size_t length = separator ? (size_t)(separator - path) : strlen(path);
        size_t capacity = length + strlen(call->file) + 2;
        char *candidate = malloc(capacity);
        if (!candidate) return _ENOMEM;
        if (length) {
            memcpy(candidate, path, length);
            candidate[length] = '/';
            memcpy(candidate + length + 1, call->file, strlen(call->file) + 1);
        }
        else snprintf(candidate, capacity, "%s", call->file);
        int result = do_execve(candidate, call->argc, call->argv, call->environment);
        free(candidate);
        if (!result) return 0;
        if (result == _EACCES) denied = 1;
        else if (result != _ENOENT && result != _ENOTDIR) return result;
        if (!separator) break;
        path = separator + 1;
    }
    return denied ? _EACCES : _ENOENT;
}

static void *run_invocation(void *pointer) {
    struct invocation *call = pointer;
    block_host_pipe_signal();
    int result = become_new_init_child();
    if (result < 0) {
        for (int i=0; i<3; i++) close(call->fd[i]);
        pthread_mutex_lock(&state_lock);
        struct invocation **position = &invocations;
        while (*position && *position != call) position = &(*position)->next;
        if (*position) *position = call->next;
        call->finished = 1;
        pthread_mutex_unlock(&state_lock);
        startup_ready(call, result);
        release_invocation(call);
        return NULL;
    }
    current->thread = pthread_self();
    current->group->fs_context = call->scope_id;
    pthread_mutex_lock(&state_lock);
    call->pid = current->pid;
    pthread_mutex_unlock(&state_lock);
    result = create_piped_stdio_from_fds(call->fd[0], call->fd[1], call->fd[2]);
    if (!result) {
        struct fd *working = generic_open(call->cwd, O_RDONLY_ | O_DIRECTORY_, 0);
        if (IS_ERR(working)) result = (int)PTR_ERR(working);
        else fs_chdir(current->fs, working);
    }
    if (!result) result = execute_guest_file(call);
    startup_ready(call, result);
    if (result < 0) do_exit(127 << 8);
    task_run_current();
    return NULL;
}

int InkNodeGuestSpawn(const char *file, int argc, const char *argv, size_t argv_size,
    const char *environment, size_t environment_size, const char *cwd,
    const int descriptors[3], uint32_t scope_id,
    InkGuestExitCallback callback, void *context, int *pid, uint32_t *resolved_scope) {
    *pid=0;*resolved_scope=0;
    if (!find_execution_scope(scope_id, NULL)) {
        for (int i=0; i<3; i++) close(descriptors[i]);
        return _EACCES;
    }
    struct invocation *call = calloc(1, sizeof(*call));
    if (!call) {
        for (int i=0; i<3; i++) close(descriptors[i]);
        return _ENOMEM;
    }
    uint32_t owner=new_invocation_scope(scope_id);
    if(!owner){free(call);for(int i=0;i<3;i++)close(descriptors[i]);return _ENOMEM;}
    call->file = strdup(file); call->cwd = strdup(cwd);
    call->argv = malloc(argv_size); call->environment = malloc(environment_size);
    if (!call->file || !call->cwd || !call->argv || !call->environment) {
        free(call->file); free(call->cwd); free(call->argv); free(call->environment); free(call);
        for (int i=0; i<3; i++) close(descriptors[i]);
        return _ENOMEM;
    }
    memcpy(call->argv, argv, argv_size); memcpy(call->environment, environment, environment_size);
    call->argc = argc; call->callback = callback; call->context = context; call->references = 2;
    call->scope_id = owner;
    memcpy(call->fd, descriptors, sizeof(call->fd));
    pthread_mutex_lock(&state_lock);
    call->next = invocations; invocations = call;
    pthread_t thread;
    int error = pthread_create(&thread, NULL, run_invocation, call);
    if (error) {
        invocations = call->next;
        pthread_mutex_unlock(&state_lock);
        call->references = 1;
        release_invocation(call);
        for (int i=0; i<3; i++) close(descriptors[i]);
        return _EAGAIN;
    }
    pthread_detach(thread);
    while (!call->started || (call->startup < 0 && !call->finished))
        pthread_cond_wait(&state_changed, &state_lock);
    int result = call->startup;
    *pid = result < 0 ? 0 : call->pid;
    *resolved_scope=result<0?0:call->scope_id;
    pthread_mutex_unlock(&state_lock);
    release_invocation(call);
    return result;
}

int InkNodeGuestKillGroup(int pid, int signal_number,uint32_t scope) {
    // Only guest process groups are addressed; host kill()/process.kill() is never called.
    return pid>1?scoped_signal(-pid,signal_number,scope,0,0):_ESRCH;
}

int InkNodeGuestKillProcess(int pid, int signal_number,uint32_t scope) {
    return pid>1?scoped_signal(pid,signal_number,scope,0,0):_ESRCH;
}
