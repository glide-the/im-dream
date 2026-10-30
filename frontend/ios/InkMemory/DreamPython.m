// [Input] Signed CPython framework, bundled standard library, dependencies and Dream sources.
// [Output] In-process execution of mobile_runtime.ios, with the GIL released between calls.
// [Pos] Minimal CPython embedding adapter; no subprocess, socket server or remote fallback.
// [Sync] 2026-10-25: initialize isolated CPython and invoke the real FastAPI backend entry.
// [Sync] 2026-10-25: expose target memory observations through a fixed CPython native module.
#import "DreamPython.h"
#include <Python/Python.h>
#include <TargetConditionals.h>
#include <os/proc.h>
#include <mach/mach.h>

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

static PyMethodDef IMNativeMethods[] = {
    {"available_memory", IMAvailableMemory, METH_NOARGS, "Read actual target memory headroom."},
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
    if (!Py_IsInitialized() && !IMInitialize(resources, error)) return nil;
    PyGILState_STATE gil = PyGILState_Ensure();
    PyObject *module = PyImport_ImportModule("mobile_runtime.ios");
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
    return value;
}
