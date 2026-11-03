// [Sync] 2026-10-31: share bounded, cancellable URLSession Admin HTTP with embedded Node and CPython; original business/authentication remain upstream.
// [Input] Signed CPython framework, bundled standard library, dependencies and Dream sources.
// [Output] In-process execution of mobile_runtime.ios, with the GIL released between calls.
// [Pos] Minimal CPython embedding adapter; no subprocess, socket server or remote fallback.
// [Sync] 2026-10-25: initialize isolated CPython and invoke the real FastAPI backend entry.
// [Sync] 2026-10-25: expose target memory observations through a fixed CPython native module.
// [Sync] 2026-11-02: measure startup-only interpreter, GIL, import, entry and Admin native wait without recording payloads.
#import "DreamPython.h"
#include "DreamHTTP.h"
#include <Python/Python.h>
#include <TargetConditionals.h>
#include <os/proc.h>
#include <mach/mach.h>
#include <sys/resource.h>
#include <stdatomic.h>
#include <unistd.h>

// start() waits on the ASGI thread; its Admin callback can run on that other thread.
static _Atomic unsigned int IMStartupCalls = 0;
typedef struct { double wall; double cpu; } IMStartupSample;
static IMStartupSample IMStartupNow(void) {
    struct rusage usage = {0};
    getrusage(RUSAGE_SELF, &usage);
    double cpu = usage.ru_utime.tv_sec + usage.ru_utime.tv_usec / 1e6
               + usage.ru_stime.tv_sec + usage.ru_stime.tv_usec / 1e6;
    return (IMStartupSample){NSProcessInfo.processInfo.systemUptime, cpu};
}
static void IMStartupLog(const char *phase, IMStartupSample start, BOOL success) {
    IMStartupSample end = IMStartupNow();
    fprintf(stderr, "DREAM_STARTUP {\"layer\":\"cpython\",\"phase\":\"%s\",\"outcome\":\"%s\",\"elapsedMs\":%.3f,\"processCpuMs\":%.3f,\"timestampMs\":%.0f,\"pid\":%d}\n",
            phase, success ? "ok" : "failed", (end.wall - start.wall) * 1000,
            (end.cpu - start.cpu) * 1000, NSDate.date.timeIntervalSince1970 * 1000, getpid());
}

static PyObject *IMAvailableMemory(PyObject *self, PyObject *args) {
#if TARGET_OS_SIMULATOR
    // Simulator processes have no iPhone jetsam allowance. Observe the host's
    // actual reusable pages; the production admission comparisons stay shared.
    vm_statistics64_data_t statistics;
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    mach_port_t host = mach_host_self();
    vm_size_t pageSize = 0;
    kern_return_t pageResult = host_page_size(host, &pageSize);
    kern_return_t result = host_statistics64(host, HOST_VM_INFO64, (host_info64_t)&statistics, &count);
    mach_port_deallocate(mach_task_self(), host);
    if (result != KERN_SUCCESS || pageResult != KERN_SUCCESS) {
        return PyErr_Format(PyExc_RuntimeError, "DREAM_IOS_MEMORY_UNAVAILABLE");
    }
    uint64_t bytes = ((uint64_t)statistics.free_count + statistics.inactive_count) * pageSize;
#else
    // A physical iPhone's zero observation is genuine exhaustion and is kept.
    uint64_t bytes = os_proc_available_memory();
#endif
    return PyLong_FromUnsignedLongLong(bytes);
}

static PyObject *IMAdminHTTP(PyObject *self, PyObject *args) {
    const char *payload;
    if (!PyArg_ParseTuple(args, "s", &payload)) return NULL;
    BOOL measure = atomic_load_explicit(&IMStartupCalls, memory_order_relaxed) > 0;
    IMStartupSample waiting = measure ? IMStartupNow() : (IMStartupSample){0};
    char *response;
    Py_BEGIN_ALLOW_THREADS
    response = IMDreamHTTPPerform(payload, NULL, NULL);
    Py_END_ALLOW_THREADS
    // A returned native JSON envelope keeps its original HTTP outcome upstream.
    if (measure) IMStartupLog("admin_http_wait", waiting, response != NULL);
    if (!response) return PyErr_NoMemory();
    PyObject *result = PyUnicode_FromString(response);
    free(response);
    return result;
}

static PyMethodDef IMNativeMethods[] = {
    {"available_memory", IMAvailableMemory, METH_NOARGS, "Read actual target memory headroom."},
    {"admin_http", IMAdminHTTP, METH_VARARGS, "Perform one bounded Admin HTTP request through iOS."},
    {NULL, NULL, 0, NULL},
};
static struct PyModuleDef IMNativeModule = {PyModuleDef_HEAD_INIT, "_dream_native", NULL, -1, IMNativeMethods};
static PyObject *IMNativeInit(void) { return PyModule_Create(&IMNativeModule); }

static void IMSetError(NSError **error, NSString *message) {
    if (error) *error = [NSError errorWithDomain:@"InkMemory.DreamPython" code:1
                                      userInfo:@{NSLocalizedDescriptionKey: message}];
}

static BOOL IMInitialize(NSString *resources, NSError **error) {
    if (PyImport_AppendInittab("_dream_native", IMNativeInit) == -1) {
        IMSetError(error, @"Python native module registration failed.");
        return NO;
    }
    PyPreConfig preconfig;
    PyPreConfig_InitIsolatedConfig(&preconfig);
    preconfig.utf8_mode = 1;
    PyStatus status = Py_PreInitialize(&preconfig);
    if (PyStatus_Exception(status)) {
        IMSetError(error, @"Python UTF-8 initialization failed.");
        return NO;
    }
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;
    config.buffered_stdio = 0;
    // The interpreter runs on a dedicated queue; UIKit owns process signals.
    config.install_signal_handlers = 0;
    config.site_import = 0;
    status = PyConfig_SetBytesString(&config, &config.home,
                                    [resources stringByAppendingPathComponent:@"python"].fileSystemRepresentation);
    if (!PyStatus_Exception(status)) {
        config.module_search_paths_set = 1;
        for (NSString *relative in @[@"python/lib/python3.13", @"python/lib/python3.13/lib-dynload", @"app", @"app_packages"]) {
            wchar_t *path = Py_DecodeLocale([resources stringByAppendingPathComponent:relative].fileSystemRepresentation, NULL);
            if (!path) { status = PyStatus_NoMemory(); break; }
            status = PyWideStringList_Append(&config.module_search_paths, path);
            PyMem_RawFree(path);
            if (PyStatus_Exception(status)) break;
        }
    }
    if (!PyStatus_Exception(status)) status = Py_InitializeFromConfig(&config);
    if (PyStatus_Exception(status)) {
        NSString *message = status.err_msg ? [NSString stringWithUTF8String:status.err_msg] : @"Python initialization failed.";
        IMSetError(error, message);
        PyConfig_Clear(&config);
        return NO;
    }
    PyConfig_Clear(&config);
    PyEval_SaveThread();
    return YES;
}

NSString *IMDreamPythonCall(NSString *resources, NSString *function, NSString *payload, NSError **error) {
    BOOL startup = [function isEqualToString:@"start"];
    if (startup) atomic_fetch_add_explicit(&IMStartupCalls, 1, memory_order_relaxed);
    if (!Py_IsInitialized()) {
        IMStartupSample initialization = IMStartupNow();
        BOOL initialized = IMInitialize(resources, error);
        IMStartupLog("interpreter_initialize", initialization, initialized);
        if (!initialized) {
            if (startup) atomic_fetch_sub_explicit(&IMStartupCalls, 1, memory_order_relaxed);
            return nil;
        }
    }
    IMStartupSample entered = startup ? IMStartupNow() : (IMStartupSample){0};
    PyGILState_STATE gil = PyGILState_Ensure();
    if (startup) IMStartupLog("gil_acquire", entered, YES);
    IMStartupSample importing = startup ? IMStartupNow() : (IMStartupSample){0};
    PyObject *module = PyImport_ImportModule("mobile_runtime.ios");
    if (startup) IMStartupLog("entry_module_import", importing, module != NULL);
    IMStartupSample invocation = startup ? IMStartupNow() : (IMStartupSample){0};
    PyObject *callable = module ? PyObject_GetAttrString(module, function.UTF8String) : NULL;
    PyObject *argument = payload ? PyUnicode_FromString(payload.UTF8String) : NULL;
    PyObject *result = callable && (!payload || argument) ? (payload ? PyObject_CallOneArg(callable, argument) : PyObject_CallNoArgs(callable)) : NULL;
    NSString *value = nil;
    if (result && PyUnicode_Check(result)) {
        const char *utf8 = PyUnicode_AsUTF8(result);
        if (utf8) value = [NSString stringWithUTF8String:utf8];
    }
    if (!value) {
        PyObject *exception = PyErr_GetRaisedException();
        PyObject *description = exception ? PyObject_Str(exception) : NULL;
        const char *utf8 = description ? PyUnicode_AsUTF8(description) : NULL;
        IMSetError(error, utf8 ? [NSString stringWithUTF8String:utf8] : @"Dream Python did not return JSON.");
        Py_XDECREF(description);
        Py_XDECREF(exception);
        PyErr_Clear();
    }
    Py_XDECREF(result);
    Py_XDECREF(argument);
    Py_XDECREF(callable);
    Py_XDECREF(module);
    PyGILState_Release(gil);
    if (startup) IMStartupLog(payload ? "runtime_bind_entry" : "public_bootstrap_entry", invocation, value != nil);
    if (startup) atomic_fetch_sub_explicit(&IMStartupCalls, 1, memory_order_relaxed);
    return value;
}
