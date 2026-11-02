// [Input] Original filesystem rule arrays and the fork-inherited execution scope.
// [Output] Guarded path/fd operations inside the mounted qualification root.
// [Pos] Explicit realfs/proc-path qualification source, excluded from production Xcode targets.
#include "node_guest_filesystem_fixture.h"
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#include "kernel/calls.h"
#include "fs/devices.h"
#include "fs/real.h"
#include "fs/tty.h"

static struct fs_ops guarded_fs;
static struct fd_ops guarded_fd;
static pthread_once_t initialized = PTHREAD_ONCE_INIT;
static pthread_mutex_t filesystem_lock = PTHREAD_MUTEX_INITIALIZER;
struct opened_path { uint32_t scope; char path[MAX_PATH]; };

static int normalized_path(const char *path) {
    if (!path || *path != '/' || strlen(path) >= MAX_PATH) return 0;
    if (strpbrk(path, "*?[]")) return 0; // Original projection must expand unsupported globs first.
    if (!strcmp(path, "/")) return 1;
    for (const char *part = path + 1; *part;) {
        const char *end = strchr(part, '/');
        size_t size = end ? (size_t)(end - part) : strlen(part);
        if (!size || (size == 1 && part[0] == '.') ||
            (size == 2 && part[0] == '.' && part[1] == '.')) return 0;
        if (!end) break;
        part = end + 1;
        if (!*part) return 0;
    }
    return 1;
}

void InkNodeGuestFreeFilesystemRules(struct InkGuestFilesystemRules *rules) {
    struct InkGuestPaths *lists[] = {&rules->denyRead, &rules->allowRead, &rules->allowWrite, &rules->denyWrite};
    for (size_t n=0; n<4; n++) {
        for (size_t k=0; k<lists[n]->count; k++) free((void *)lists[n]->items[k]);
        free((void *)lists[n]->items); *lists[n] = (struct InkGuestPaths){};
    }
}

int InkNodeGuestCopyFilesystemRules(struct InkGuestFilesystemRules *target,
        const struct InkGuestFilesystemRules *source) {
    *target = (struct InkGuestFilesystemRules){};
    if (!source) return _EINVAL;
    const struct InkGuestPaths *from[] = {&source->denyRead, &source->allowRead, &source->allowWrite, &source->denyWrite};
    struct InkGuestPaths *to[] = {&target->denyRead, &target->allowRead, &target->allowWrite, &target->denyWrite};
    int result = _ENOMEM;
    for (size_t n=0; n<4; n++) {
        if (from[n]->count && !from[n]->items) {result = _EINVAL; goto fail;}
        char **items = calloc(from[n]->count, sizeof(*items));
        if (from[n]->count && !items) goto fail;
        to[n]->items = (const char *const *)items;
        for (size_t k=0; k<from[n]->count; k++) {
            if (!normalized_path(from[n]->items[k])) {result = _EINVAL; goto fail;}
            items[k] = strdup(from[n]->items[k]);
            if (!items[k]) goto fail;
            to[n]->count++;
        }
    }
    return 0;
fail:
    InkNodeGuestFreeFilesystemRules(target);
    return result;
}

static int within(const char *path, const char *root) {
    size_t size = strlen(root);
    return !strcmp(root, "/") || (!strncmp(path, root, size) && (!path[size] || path[size] == '/'));
}
static size_t match(const char *path, struct InkGuestPaths paths) {
    size_t best = 0;
    for (size_t n=0; n<paths.count; n++)
        if (within(path, paths.items[n]) && strlen(paths.items[n]) > best) best = strlen(paths.items[n]);
    return best;
}
static int allowed(const struct InkGuestFilesystemRules *rules, const char *path, int writing) {
    if (!rules) return !current || current->pid == 1;
    if (writing) return match(path, rules->allowWrite) && !match(path, rules->denyWrite);
    size_t denied = match(path, rules->denyRead);
    return !denied || match(path, rules->allowRead) > denied;
}
int InkNodeGuestFilesystemPathAllowed(uint32_t scope,const char *path,int writing) {
    return normalized_path(path) && allowed(InkNodeGuestFilesystemRulesForScope(scope),path,writing) ? 0 : _EACCES;
}
static const struct InkGuestFilesystemRules *current_rules(void) {
    return current && current->group ? InkNodeGuestFilesystemRulesForScope((uint32_t)current->group->fs_context) : NULL;
}
static int removable(const struct InkGuestFilesystemRules *rules, const char *path) {
    if (!allowed(rules, path, 1)) return 0;
    if (!rules) return 1;
    const struct InkGuestPaths lists[] = {rules->denyRead, rules->denyWrite};
    for (size_t n=0; n<2; n++) for (size_t k=0; k<lists[n].count; k++)
        if (within(lists[n].items[k], path)) return 0;
    return 1;
}

static int guest_path(struct mount *mount, const char *path, char output[MAX_PATH]) {
    const char *point = mount->point;
    if (!point || !strcmp(point, "/")) point = "";
    int size = snprintf(output, MAX_PATH, "%s%s%s", point, *path == '/' ? "" : "/", path);
    if (size < 0 || size >= MAX_PATH) return _ENAMETOOLONG;
    return normalized_path(output) ? 0 : _EACCES;
}

// Every native path operation uses retained parent descriptors and O_NOFOLLOW.
// Serialize guest mutations so a guest rename cannot race policy checks in another task.
static int parent_fd(struct mount *mount, const char *path, char leaf[MAX_PATH]) {
    if (strlen(path) >= MAX_PATH) return _ENAMETOOLONG;
    char copy[MAX_PATH]; strcpy(copy, path);
    char *part = copy;
    while (*part == '/') part++;
    int parent = dup(mount->root_fd);
    if (parent < 0) return errno_map();
    if (!*part) {strcpy(leaf, "."); return parent;}
    for (;;) {
        char *separator = strchr(part, '/');
        if (separator) *separator = 0;
        if (!*part || !strcmp(part, ".") || !strcmp(part, "..")) {close(parent); return _EACCES;}
        if (!separator) {strcpy(leaf, part); return parent;}
        int child = openat(parent, part, O_RDONLY | O_NOFOLLOW | O_NONBLOCK);
        int error = child < 0 ? errno_map() : 0;
        struct stat metadata;
        if (!error && fstat(child, &metadata) < 0) error = errno_map();
        if (!error && !S_ISDIR(metadata.st_mode)) error = _ENOTDIR;
        close(parent);
        if (error) {if (child >= 0) close(child); return error;}
        parent = child; part = separator + 1;
    }
}

static int relative_host_fd(int root_fd, int fd, const char *point, char output[MAX_PATH]) {
    char root[MAX_PATH], actual[MAX_PATH];
    if (fcntl(root_fd, F_GETPATH, root) < 0 || fcntl(fd, F_GETPATH, actual) < 0) return _EACCES;
    size_t length = strlen(root);
    if (!within(actual, root)) return _EACCES;
    const char *relative = !strcmp(root, "/") ? actual : actual + length;
    if (!*relative) relative = "/";
    if (!point || !strcmp(point, "/")) point = "";
    int size = snprintf(output, MAX_PATH, "%s%s", point, relative);
    return size >= 0 && size < MAX_PATH && normalized_path(output) ? 0 : _EACCES;
}

static int descriptor_allowed(struct fd *fd, int writing) {
    const struct InkGuestFilesystemRules *rules = current_rules();
    struct opened_path *original = fd->fs_data;
    uint32_t scope = current && current->group ? current->group->fs_context : 0;
    if (original && original->scope && original->scope != scope) return _EACCES;
    char path[MAX_PATH];
    int result = relative_host_fd(fd->mount->root_fd, fd->real_fd, fd->mount->point, path);
    if (result) {
        struct stat metadata;
        if (!original || original->scope != scope || fstat(fd->real_fd, &metadata) || metadata.st_nlink)
            return _EACCES;
        strcpy(path, original->path); // An unlinked owned description retains its original scope.
    }
    if (!allowed(rules, path, writing) || (original && !allowed(rules, original->path, writing)))
        return _EACCES;
    return 0;
}

int InkNodeGuestInheritedFileAllowed(const char *root, uint32_t scope, int fd, int writing) {
    const struct InkGuestFilesystemRules *rules = InkNodeGuestFilesystemRulesForScope(scope);
    if (!rules) return _EACCES;
    struct stat metadata;
    if (fstat(fd, &metadata)) return errno_map();
    if (S_ISFIFO(metadata.st_mode)) return 0;
    if (!S_ISREG(metadata.st_mode)) return _EACCES;
    pthread_mutex_lock(&filesystem_lock);
    int root_fd = open(root, O_RDONLY | O_NOFOLLOW);
    char path[MAX_PATH];
    int result = root_fd < 0 ? _EACCES : relative_host_fd(root_fd, fd, "", path);
    if (!result && !allowed(rules, path, writing)) result = _EACCES;
    if (root_fd >= 0) close(root_fd);
    pthread_mutex_unlock(&filesystem_lock);
    return result;
}

static struct fd *guarded_open(struct mount *mount, const char *path, int flags, int mode) {
    pthread_mutex_lock(&filesystem_lock);
    char full[MAX_PATH], leaf[MAX_PATH];
    int result = guest_path(mount, path, full), parent = -1;
    const struct InkGuestFilesystemRules *rules = current_rules();
    int writing = flags & (O_WRONLY_ | O_RDWR_ | O_CREAT_ | O_TRUNC_ | O_APPEND_);
    if (!result && writing && !allowed(rules, full, 1)) result = _EACCES;
    if (!result) {parent = parent_fd(mount, path, leaf); if (parent < 0) result = parent;}
    if (!result && (flags & O_ACCMODE_) != O_WRONLY_ && !allowed(rules, full, 0)) {
        struct stat metadata;
        if (writing || fstatat(parent, leaf, &metadata, AT_SYMLINK_NOFOLLOW) || !S_ISDIR(metadata.st_mode))
            result = _EACCES;
    }
    struct fd *opened = ERR_PTR(result);
    if (!result) {
        struct mount local = *mount; local.root_fd = parent;
        struct stat metadata;
        int fifo = !fstatat(parent,leaf,&metadata,AT_SYMLINK_NOFOLLOW) && S_ISFIFO(metadata.st_mode);
        // A FIFO open may wait for its peer. Keep the parent fd pinned, release the mutation lock.
        if (fifo) pthread_mutex_unlock(&filesystem_lock);
        opened = realfs.open(&local, leaf, flags | O_NOFOLLOW_, mode);
        if (fifo) pthread_mutex_lock(&filesystem_lock);
        if (!IS_ERR(opened)) {
            struct opened_path *original = calloc(1, sizeof(*original));
            if (!original) {fd_close(opened); opened = ERR_PTR(_ENOMEM);}
            else {
                original->scope = current && current->group ? current->group->fs_context : 0;
                strcpy(original->path, full); opened->fs_data = original; opened->ops = &guarded_fd;
            }
        }
    }
    if (parent >= 0) close(parent);
    pthread_mutex_unlock(&filesystem_lock);
    return opened;
}

static int guarded_close(struct fd *fd) {
    free(fd->fs_data); fd->fs_data = NULL;
    return realfs.close(fd);
}

static dev_t_ device_number(const char *path) {
    // Preserve the pinned realfs placeholder-device mapping through parent-fd traversal.
    if (!strncmp(path, "/dev/", 5)) {
        const char *name = path + 5;
        if (!strcmp(name,"null")) return dev_make(MEM_MAJOR,DEV_NULL_MINOR);
        if (!strcmp(name,"zero")) return dev_make(MEM_MAJOR,DEV_ZERO_MINOR);
        if (!strcmp(name,"full")) return dev_make(MEM_MAJOR,DEV_FULL_MINOR);
        if (!strcmp(name,"random")) return dev_make(MEM_MAJOR,DEV_RANDOM_MINOR);
        if (!strcmp(name,"urandom")) return dev_make(MEM_MAJOR,DEV_URANDOM_MINOR);
        if (!strcmp(name,"tty")) return dev_make(TTY_ALTERNATE_MAJOR,DEV_TTY_MINOR);
        if (!strcmp(name,"console")) return dev_make(TTY_ALTERNATE_MAJOR,DEV_CONSOLE_MINOR);
        if (!strcmp(name,"ptmx")) return dev_make(TTY_ALTERNATE_MAJOR,DEV_PTMX_MINOR);
    }
    return 0;
}
static int guarded_stat(struct mount *mount, const char *path, struct statbuf *metadata) {
    pthread_mutex_lock(&filesystem_lock);
    char full[MAX_PATH], leaf[MAX_PATH]; int parent = -1;
    int result = guest_path(mount, path, full);
    if (!result) {parent = parent_fd(mount,path,leaf); if (parent < 0) result = parent;}
    if (!result) {
        struct mount local = *mount; local.root_fd = parent;
        result = realfs.stat(&local,leaf,metadata);
        if (!result && !S_ISDIR(metadata->mode) && !allowed(current_rules(),full,0)) result = _EACCES;
        dev_t_ device = device_number(full);
        if (!result && device) {metadata->mode = S_IFCHR | 0666; metadata->rdev = device;}
    }
    if (parent >= 0) close(parent);
    pthread_mutex_unlock(&filesystem_lock); return result;
}
static int guarded_fstat(struct fd *fd,struct statbuf *metadata) {
    pthread_mutex_lock(&filesystem_lock);
    int result=realfs.fstat(fd,metadata);
    struct opened_path *original=fd->fs_data;
    if(!result && S_ISDIR(metadata->mode)) {
        // Original srt permits directory metadata. construct_task opens root before scope binding.
        char path[MAX_PATH];
        result=relative_host_fd(fd->mount->root_fd,fd->real_fd,fd->mount->point,path);
        uint32_t scope=current&&current->group?current->group->fs_context:0;
        if(original && original->scope && original->scope!=scope)result=_EACCES;
    } else if(!result)result=descriptor_allowed(fd,0);
    dev_t_ device=original?device_number(original->path):0;
    if(!result && device){metadata->mode=S_IFCHR|0666;metadata->rdev=device;}
    pthread_mutex_unlock(&filesystem_lock);return result;
}
static ssize_t guarded_readlink(struct mount *mount,const char *path,char *buffer,size_t size) {
    pthread_mutex_lock(&filesystem_lock);
    char full[MAX_PATH], leaf[MAX_PATH]; int parent = -1;
    ssize_t result = guest_path(mount,path,full);
    if (!result && !allowed(current_rules(),full,0)) result = _EACCES;
    if (!result) {parent = parent_fd(mount,path,leaf); if (parent < 0) result = parent;}
    if (!result) {struct mount local=*mount;local.root_fd=parent;result=realfs.readlink(&local,leaf,buffer,size);}
    if (parent >= 0) close(parent);
    pthread_mutex_unlock(&filesystem_lock); return result;
}

enum path_operation {remove_file, remove_directory, create_directory, create_node, set_attribute, set_time};
static int change_path(struct mount *mount,const char *path,enum path_operation operation,
        mode_t_ mode,dev_t_ device,struct attr attribute,struct timespec atime,struct timespec mtime) {
    pthread_mutex_lock(&filesystem_lock);
    char full[MAX_PATH],leaf[MAX_PATH];int parent=-1;
    int result=guest_path(mount,path,full);
    const struct InkGuestFilesystemRules *rules=current_rules();
    if(!result && operation==create_directory) {
        parent=parent_fd(mount,path,leaf);
        if(parent<0)result=parent;
        else {
            struct stat existing;
            // mkdir -p probes existing ancestors, including a read-only root.
            if(!fstatat(parent,leaf,&existing,AT_SYMLINK_NOFOLLOW) && S_ISDIR(existing.st_mode)) result=_EEXIST;
        }
    }
    if (!result && (!allowed(rules,full,1) ||
        ((operation==remove_file || operation==remove_directory) && !removable(rules,full)))) result=_EACCES;
    if (!result && parent<0) {parent=parent_fd(mount,path,leaf);if(parent<0)result=parent;}
    if (!result) {
        struct mount local=*mount;local.root_fd=parent;
        switch(operation) {
            case remove_file:result=realfs.unlink(&local,leaf);break;
            case remove_directory:result=realfs.rmdir(&local,leaf);break;
            case create_directory:result=realfs.mkdir(&local,leaf,mode);break;
            case create_node:
                if(S_ISFIFO(mode))result=mkfifoat(parent,leaf,mode&0777)<0?errno_map():0;
                else result=realfs.mknod(&local,leaf,mode,device);
                break;
            case set_attribute:
            case set_time: {
                int descriptor=openat(parent,leaf,O_NOFOLLOW|O_NONBLOCK|(operation==set_attribute && attribute.type==attr_size?O_WRONLY:O_RDONLY));
                if(descriptor<0)result=errno_map();
                else {
                    struct fd temporary={.real_fd=descriptor};
                    if(operation==set_attribute)result=realfs.fsetattr(&temporary,attribute);
                    else {struct timespec times[]={atime,mtime};result=futimens(descriptor,times)<0?errno_map():0;}
                    close(descriptor);
                }
                break;
            }
        }
    }
    if(parent>=0)close(parent);
    pthread_mutex_unlock(&filesystem_lock);return result;
}
#define CHANGE(name,kind) static int name(struct mount *m,const char *p) {return change_path(m,p,kind,0,0,(struct attr){},(struct timespec){},(struct timespec){});}
CHANGE(guarded_unlink,remove_file)
CHANGE(guarded_rmdir,remove_directory)
static int guarded_mkdir(struct mount*m,const char*p,mode_t_ mode){return change_path(m,p,create_directory,mode,0,(struct attr){},(struct timespec){},(struct timespec){});}
static int guarded_mknod(struct mount*m,const char*p,mode_t_ mode,dev_t_ dev){return change_path(m,p,create_node,mode,dev,(struct attr){},(struct timespec){},(struct timespec){});}
static int guarded_setattr(struct mount*m,const char*p,struct attr a){return change_path(m,p,set_attribute,0,0,a,(struct timespec){},(struct timespec){});}
static int guarded_utime(struct mount*m,const char*p,struct timespec a,struct timespec b){return change_path(m,p,set_time,0,0,(struct attr){},a,b);}

static int move_path(struct mount *mount,const char *source,const char *destination,int linking) {
    pthread_mutex_lock(&filesystem_lock);
    char from[MAX_PATH],to[MAX_PATH],left[MAX_PATH],right[MAX_PATH];int src=-1,dst=-1;
    int result=guest_path(mount,source,from);
    if(!result)result=guest_path(mount,destination,to);
    const struct InkGuestFilesystemRules *rules=current_rules();
    if(!result && (!removable(rules,from) || !removable(rules,to) || (linking && !allowed(rules,from,0)))) result=_EACCES;
    if(!result){src=parent_fd(mount,source,left);if(src<0)result=src;}
    if(!result){dst=parent_fd(mount,destination,right);if(dst<0)result=dst;}
    if(!result){int native=linking?linkat(src,left,dst,right,0):renameat(src,left,dst,right);result=native<0?errno_map():0;}
    if(src>=0)close(src);if(dst>=0)close(dst);
    pthread_mutex_unlock(&filesystem_lock);return result;
}
static int guarded_link(struct mount*m,const char*a,const char*b){return move_path(m,a,b,1);}
static int guarded_rename(struct mount*m,const char*a,const char*b){return move_path(m,a,b,0);}
static int guarded_symlink(struct mount *mount,const char *target,const char *path) {
    pthread_mutex_lock(&filesystem_lock);
    char full[MAX_PATH],leaf[MAX_PATH];int parent=-1,result=guest_path(mount,path,full);
    if(!result && !allowed(current_rules(),full,1))result=_EACCES;
    if(!result){parent=parent_fd(mount,path,leaf);if(parent<0)result=parent;}
    if(!result){struct mount local=*mount;local.root_fd=parent;result=realfs.symlink(&local,target,leaf);}
    if(parent>=0)close(parent);
    pthread_mutex_unlock(&filesystem_lock);return result;
}

#define IO_WRAPPER(name,field,writing,signature,arguments) \
static ssize_t name signature { \
    pthread_mutex_lock(&filesystem_lock);int check=descriptor_allowed(fd,writing); \
    int fifo=S_ISFIFO(fd->type);if(fifo)pthread_mutex_unlock(&filesystem_lock); \
    ssize_t result=check?check:realfs_fdops.field arguments; \
    if(!fifo)pthread_mutex_unlock(&filesystem_lock);return result;}
IO_WRAPPER(guarded_read,read,0,(struct fd *fd,void*b,size_t n),(fd,b,n))
IO_WRAPPER(guarded_write,write,1,(struct fd *fd,const void*b,size_t n),(fd,b,n))
IO_WRAPPER(guarded_pread,pread,0,(struct fd *fd,void*b,size_t n,off_t o),(fd,b,n,o))
IO_WRAPPER(guarded_pwrite,pwrite,1,(struct fd *fd,const void*b,size_t n,off_t o),(fd,b,n,o))
static int guarded_readdir(struct fd *fd,struct dir_entry *entry) {
    pthread_mutex_lock(&filesystem_lock);int result=descriptor_allowed(fd,0);
    if(!result)result=realfs_fdops.readdir(fd,entry);
    pthread_mutex_unlock(&filesystem_lock);return result;
}
static int guarded_fsetattr(struct fd *fd,struct attr attribute) {
    pthread_mutex_lock(&filesystem_lock);int result=descriptor_allowed(fd,1);
    if(!result)result=realfs.fsetattr(fd,attribute);
    pthread_mutex_unlock(&filesystem_lock);return result;
}
static int guarded_mmap(struct fd *fd,struct mem *mem,page_t first,pages_t pages,off_t offset,int prot,int flags) {
    pthread_mutex_lock(&filesystem_lock);int result=descriptor_allowed(fd,0);
    if(!result && (flags&MMAP_SHARED) && (prot&P_WRITE))result=descriptor_allowed(fd,1);
    if(!result)result=realfs_fdops.mmap(fd,mem,first,pages,offset,prot,flags);
    pthread_mutex_unlock(&filesystem_lock);return result;
}
static int guarded_getpath(struct fd *fd,char *path) {
    char full[MAX_PATH];int result=relative_host_fd(fd->mount->root_fd,fd->real_fd,fd->mount->point,full);
    if(result)return result;
    const char *point=fd->mount->point;size_t length=point&&strcmp(point,"/")?strlen(point):0;
    strcpy(path,full+length);return 0;
}
static int guarded_flock(struct fd *fd,int operation) {
    pthread_mutex_lock(&filesystem_lock);int result=descriptor_allowed(fd,0),native=0;
    if(operation&LOCK_SH_)native|=LOCK_SH;if(operation&LOCK_EX_)native|=LOCK_EX;
    if(operation&LOCK_UN_)native|=LOCK_UN;if(operation&LOCK_NB_)native|=LOCK_NB;
    pthread_mutex_unlock(&filesystem_lock);
    if(!result && flock(fd->real_fd,native)<0)result=errno_map();
    return result;
}
static void initialize(void) {
    guarded_fs=realfs;guarded_fd=realfs_fdops;
    guarded_fs.name="ink-qualified-realfs";
    guarded_fs.open=guarded_open;guarded_fs.stat=guarded_stat;guarded_fs.fstat=guarded_fstat;guarded_fs.readlink=guarded_readlink;
    guarded_fs.unlink=guarded_unlink;guarded_fs.rmdir=guarded_rmdir;guarded_fs.mkdir=guarded_mkdir;
    guarded_fs.mknod=guarded_mknod;guarded_fs.link=guarded_link;guarded_fs.rename=guarded_rename;
    guarded_fs.symlink=guarded_symlink;guarded_fs.setattr=guarded_setattr;guarded_fs.fsetattr=guarded_fsetattr;
    guarded_fs.utime=guarded_utime;guarded_fs.getpath=guarded_getpath;guarded_fs.close=guarded_close;
    guarded_fs.flock=guarded_flock;
    guarded_fd.read=guarded_read;guarded_fd.write=guarded_write;guarded_fd.pread=guarded_pread;
    guarded_fd.pwrite=guarded_pwrite;guarded_fd.readdir=guarded_readdir;guarded_fd.mmap=guarded_mmap;
    guarded_fd.close=guarded_close;
}
const struct fs_ops *InkNodeGuestFilesystem(void) {pthread_once(&initialized,initialize);return &guarded_fs;}
