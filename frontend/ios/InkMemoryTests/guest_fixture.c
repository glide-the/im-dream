// [Input] Isolated application-owned ELF fixture root and private pipe descriptors.
// [Output] Actual guest Bash status and bytes; no host subprocess or business calls.
// [Pos] Named target qualification fixture; original Runtime remains unchanged.
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "kernel/calls.h"
#include "kernel/init.h"
#include "kernel/task.h"
#include "fs/path.h"
#include "fs/real.h"

struct fixture_call { const char *root; int input; int output; int error; int code; int setup; int guest_pid; };
static struct fixture_call *active_fixture;
static void fixture_exit(struct task *task, int status) {
    if (active_fixture && task->pid == active_fixture->guest_pid)
        active_fixture->code = (status & 0xff) ? 128 + (status & 0x7f) : status >> 8;
}
static void *fixture_thread(void *pointer) {
    struct fixture_call *call = pointer;
    fprintf(stderr, "IOS_POSIX_SETUP phase=mount_root\n");
    int error = mount_root(&realfs, call->root);
    if (error < 0) { call->setup = error; return NULL; }
    fprintf(stderr, "IOS_POSIX_SETUP phase=init\n");
    error = become_first_process();
    if (error < 0) { call->setup = error; return NULL; }
    current->thread = pthread_self();
    // Keep init present; guest completion must never halt the application.
    error = become_new_init_child();
    if (error < 0) { call->setup = error; return NULL; }
    current->thread = pthread_self();
    call->guest_pid = current->pid;
    struct fd *working = generic_open("/workspace", O_RDONLY_, 0);
    if (IS_ERR(working)) { call->setup = (int)PTR_ERR(working); return NULL; }
    fs_chdir(current->fs, working);
    error = create_piped_stdio_from_fds(call->input, call->output, call->error);
    if (error < 0) { call->setup = error; return NULL; }
    error = do_mount(&procfs, "proc", "/proc", "", 0);
    if (error < 0) { call->setup = error; return NULL; }
    error = do_mount(&devptsfs, "devpts", "/dev/pts", "", 0);
    if (error < 0) { call->setup = error; return NULL; }
    static const char command[] =
        "/bin/bash\0--noprofile\0--norc\0-c\0"
        "set -euo pipefail; read -r incoming; test \"$incoming\" = fixture-input; "
        "a=(one two three); count=$(printf '%s\\n' \"${a[@]}\" | /bin/busybox wc -l); "
        "test \"$count\" -eq 3; (printf 'nested\\n' > /workspace/result.txt); "
        "test \"$(/bin/busybox cat /workspace/result.txt)\" = nested; "
        "(/bin/busybox sleep 0.01; printf background-ok) & job=$!; wait \"$job\"; "
        "printf '\\nPIPE_ARRAY_SUBSHELL_WAIT_OK\\n'; /bin/busybox uname -sm; "
        "printf 'stderr-ok\\n' >&2; exit 7\0";
    static const char environment[] = "PATH=/bin:/usr/bin\0HOME=/workspace\0LANG=C\0TERM=dumb\0";
    fprintf(stderr, "IOS_POSIX_SETUP phase=exec_bash\n");
    error = do_execve("/bin/bash", 5, command, environment);
    if (error < 0) { call->setup = error; return NULL; }
    exit_hook = fixture_exit;
    fprintf(stderr, "IOS_POSIX_SETUP phase=run_guest\n");
    task_run_current();
    call->setup = -999;
    return NULL;
}
static int read_all(int fd, char *output, size_t size) {
    size_t used = 0;
    while (used + 1 < size) {
        ssize_t count = read(fd, output + used, size - used - 1);
        if (count == 0) break;
        if (count < 0) { close(fd); return -1; }
        used += (size_t)count;
    }
    output[used] = 0;
    close(fd);
    return (int)used;
}
int InkGuestRunFixture(const char *root, char *output, size_t output_size,
                       char *error_output, size_t error_size, int *guest_pid) {
    int input[2], out[2], err[2];
    if (pipe(input) || pipe(out) || pipe(err)) return -1000;
    const char line[] = "fixture-input\n";
    if (write(input[1], line, sizeof(line)-1) != sizeof(line)-1) return -1001;
    close(input[1]);
    struct sigaction old_usr1, old_pipe;
    sigaction(SIGUSR1, NULL, &old_usr1);
    sigaction(SIGPIPE, NULL, &old_pipe);
    struct fixture_call call = {root, input[0], out[1], err[1], -1002, 0, 0};
    active_fixture = &call;
    pthread_t thread;
    if (pthread_create(&thread, NULL, fixture_thread, &call)) return -1003;
    pthread_join(thread, NULL);
    exit_hook = NULL;
    active_fixture = NULL;
    sigaction(SIGUSR1, &old_usr1, NULL);
    sigaction(SIGPIPE, &old_pipe, NULL);
    *guest_pid = call.guest_pid;
    if (call.setup) {
        close(input[0]); close(out[1]); close(err[1]); close(out[0]); close(err[0]);
        return call.setup;
    }
    if (read_all(out[0], output, output_size) < 0 || read_all(err[0], error_output, error_size) < 0) return -1004;
    return call.code;
}
