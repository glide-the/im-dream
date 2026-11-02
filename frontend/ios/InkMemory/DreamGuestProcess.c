// [Input] Packaged Linux command root, App-owned paths and original Node argv/stdio.
// [Output] In-process interpreted commands with original startup/exit/stop results.
// [Pos] iOS command compatibility; Claude command sandbox is disabled by deployment configuration.
// [Sync] 2026-10-25: reuse qualified guest execution and mount original App data/resource paths.
// [Sync] 2026-10-26: compare POSIX-resolved App paths across physical-device Foundation and Node aliases.
#include "DreamGuestProcess.h"
#include <pthread.h>
#include <signal.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
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
    uint32_t generation;
    IMDreamGuestExitCallback callback;
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

static char *kernel_data, *kernel_resources;
static uint32_t next_generation = 1;

// Mount the original App paths at their original names. Commands and Node share files.
static int mount_application_path(const char *path) {
    if (!path || path[0] != '/' || strlen(path) >= MAX_PATH) return _EINVAL;
    char point[MAX_PATH]; strcpy(point,path);
    for (char *part=point+1; ; part++) {
        if (*part && *part!='/') continue;
        char saved=*part; *part=0;
        int result=generic_mkdirat(current->fs->root,point,0700);
        *part=saved;
        if (result<0 && result!=_EEXIST) return result;
        if (!saved) break;
    }
    return do_mount(&realfs,path,path,"",0);
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
    int result = mount_root(&realfs, kernel_root);
    if (!result) result = become_first_process();
    if (!result) result = mount_application_path(kernel_data);
    if (!result) result = mount_application_path(kernel_resources);
    // Preserve the application's original signal behavior on all non-guest threads.
    sigaction(SIGPIPE, &old_pipe, NULL);
    struct sigaction chained = {.sa_sigaction=guest_signal, .sa_flags=SA_SIGINFO};
    sigemptyset(&chained.sa_mask);
    sigaddset(&chained.sa_mask, SIGUSR1);
    if (!result) sigaction(SIGUSR1, &chained, NULL);
    if (!result) {
        current->thread = pthread_self();
        result = do_mount(&procfs, "proc", "/proc", "", 0);
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

int IMDreamGuestInitialize(const char *root, const char *data, const char *resources) {
    if (!root || !data || !resources) return _EINVAL;
    char *resolved_root = realpath(root, NULL);
    char *resolved_data = realpath(data, NULL);
    char *resolved_resources = realpath(resources, NULL);
    if (!resolved_root || !resolved_data || !resolved_resources) {
        free(resolved_root); free(resolved_data); free(resolved_resources);
        return _EINVAL;
    }
    pthread_mutex_lock(&state_lock);
    if (!kernel_state) {
        kernel_root = strdup(resolved_root);
        kernel_data = strdup(resolved_data);
        kernel_resources = strdup(resolved_resources);
        kernel_state = 1;
        pthread_t thread;
        int error = pthread_create(&thread, NULL, initialize_kernel, NULL);
        if (error) kernel_state = -error;
        else pthread_detach(thread);
    }
    while (kernel_state == 1) pthread_cond_wait(&state_changed, &state_lock);
    int result = kernel_state == 2 ? (strcmp(resolved_root, kernel_root) || strcmp(resolved_data, kernel_data) || strcmp(resolved_resources, kernel_resources) ? _EINVAL : 0) : kernel_state;
    pthread_mutex_unlock(&state_lock);
    free(resolved_root); free(resolved_data); free(resolved_resources);
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
    current->group->fs_context = call->generation;
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

int IMDreamGuestSpawn(const char *file, int argc, const char *argv, size_t argv_size,
    const char *environment, size_t environment_size, const char *cwd,
    const int descriptors[3],
    IMDreamGuestExitCallback callback, void *context, int *pid, uint32_t *resolved_generation) {
    *pid=0;*resolved_generation=0;
    struct invocation *call = calloc(1, sizeof(*call));
    if (!call) {
        for (int i=0; i<3; i++) close(descriptors[i]);
        return _ENOMEM;
    }
    pthread_mutex_lock(&state_lock);
    uint32_t owner = next_generation ? next_generation++ : 0;
    pthread_mutex_unlock(&state_lock);
    if (!owner) {free(call); for(int i=0;i<3;i++)close(descriptors[i]); return _EAGAIN;}
    call->file = strdup(file); call->cwd = strdup(cwd);
    call->argv = malloc(argv_size); call->environment = malloc(environment_size);
    if (!call->file || !call->cwd || !call->argv || !call->environment) {
        free(call->file); free(call->cwd); free(call->argv); free(call->environment); free(call);
        for (int i=0; i<3; i++) close(descriptors[i]);
        return _ENOMEM;
    }
    memcpy(call->argv, argv, argv_size); memcpy(call->environment, environment, environment_size);
    call->argc = argc; call->callback = callback; call->context = context; call->references = 2;
    call->generation = owner;
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
    *resolved_generation=result<0?0:call->generation;
    pthread_mutex_unlock(&state_lock);
    release_invocation(call);
    return result;
}

// Generations prevent stale native process handles from targeting a reused guest PID.
// Guest commands retain the core's ordinary Linux signal behavior.
static int signal_owned(int pid,int signal,uint32_t generation,int group) {
    if(pid<=1 || pid>=MAX_PID || !generation)return _ESRCH;
    if((unsigned)signal>=NUM_SIGS)return _EINVAL;
    int result=_ESRCH;
    lock(&pids_lock);
    for(int id=group?2:pid;id<(group?MAX_PID:pid+1);id++) {
        struct task *task=pid_get_task(id);
        if(!task || task->exiting || task->zombie || !task->group ||
            task->group->fs_context!=generation)continue;
        if(group && (!task_is_leader(task) || task->group->pgid!=pid))continue;
        send_signal(task,signal,SIGINFO_NIL);result=0;
    }
    unlock(&pids_lock);return result;
}
int IMDreamGuestKillGroup(int pid,int signal,uint32_t generation) {return signal_owned(pid,signal,generation,1);}
int IMDreamGuestKillProcess(int pid,int signal,uint32_t generation) {return signal_owned(pid,signal,generation,0);}
