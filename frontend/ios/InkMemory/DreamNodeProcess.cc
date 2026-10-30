// [Input] Original Node ChildProcess requests and App-owned guest command execution.
// [Output] Original Node pipes, startup errors and asynchronous guest exit metadata.
// [Pos] iOS original Node process compatibility; command sandbox configuration stays upstream.
// [Sync] 2026-10-25: retain invocation generations for PID/group signals and each native process handle.
// [Sync] 2026-10-25: synchronous cwd comes from the original Worker session, including default cwd calls.
// [Sync] 2026-10-25: keep Worker cleanup alive until native exit notifications close without entering a disposed isolate.
#include <node.h>
#include <node_buffer.h>
#include <uv.h>
#include <unistd.h>
#include <signal.h>
#include <fcntl.h>
#include <poll.h>
#include <errno.h>
#include <sys/stat.h>
#include <atomic>
#include <chrono>
#include <mutex>
#include <string>
#include <vector>
#include <utility>
#include "DreamGuestProcess.h"
namespace {
using namespace v8;
struct NodeProcess {
    uv_async_t notification;
    Isolate *isolate;
    Global<Context> context;
    Global<Function> callback;
    node::AsyncResource *resource;
    std::atomic<int> status{-1};
    std::mutex exitMutex;
    int pid=0;
    uint32_t generation=0;
    bool closing=false;
    node::AsyncCleanupHookHandle cleanup;
    void (*cleanupDone)(void *)=nullptr;
    void *cleanupContext=nullptr;
};
Local<String> Key(Isolate *i,const char *s) { return String::NewFromUtf8(i,s).ToLocalChecked(); }
void Set(Local<Context> c,Local<Object> o,const char *s,Local<Value> v) { o->Set(c,Key(c->GetIsolate(),s),v).Check(); }
Local<Value> Field(Local<Context> c,Local<Object> o,const char *s) { return o->Get(c,Key(c->GetIsolate(),s)).ToLocalChecked(); }
std::string Text(Isolate *i,Local<Value> v) { String::Utf8Value s(i,v); return *s?std::string(*s,s.length()):std::string(); }
std::string Strings(Local<Context> c,Local<Array> a) {
    std::string result;
    for(uint32_t i=0;i<a->Length();i++) { result+=Text(c->GetIsolate(),a->Get(c,i).ToLocalChecked()); result.push_back(0); }
    result.push_back(0); return result;
}
int GuestError(int e) {
    switch(-e) {
        case 1:return UV_EPERM; case 3:return UV_ESRCH; case 2:return UV_ENOENT; case 8:return UV_ENOEXEC; case 11:return UV_EAGAIN; case 12:return UV_ENOMEM;
        case 13:return UV_EACCES; case 20:return UV_ENOTDIR; case 22:return UV_EINVAL;
        case 24:return UV_EMFILE; default:return UV_EIO;
    }
}
const char *SignalName(int n) {
    switch(n) {
        case 1:return "SIGHUP"; case 2:return "SIGINT"; case 3:return "SIGQUIT";
        case 4:return "SIGILL"; case 5:return "SIGTRAP"; case 6:return "SIGABRT";
        case 7:return "SIGBUS"; case 8:return "SIGFPE"; case 9:return "SIGKILL";
        case 10:return "SIGUSR1"; case 11:return "SIGSEGV"; case 12:return "SIGUSR2";
        case 13:return "SIGPIPE"; case 14:return "SIGALRM"; case 15:return "SIGTERM";
        case 17:return "SIGCHLD"; case 18:return "SIGCONT"; case 19:return "SIGSTOP";
        case 20:return "SIGTSTP"; case 21:return "SIGTTIN"; case 22:return "SIGTTOU";
        case 23:return "SIGURG"; case 24:return "SIGXCPU"; case 25:return "SIGXFSZ";
        case 26:return "SIGVTALRM"; case 27:return "SIGPROF"; case 28:return "SIGWINCH";
        case 29:return "SIGIO"; case 31:return "SIGSYS";
        default:return "UNKNOWN";
    }
}
int LinuxSignal(int n) {
    const int host[]={0,SIGHUP,SIGINT,SIGQUIT,SIGILL,SIGTRAP,SIGABRT,SIGBUS,SIGFPE,SIGKILL,SIGUSR1,SIGSEGV,SIGUSR2,SIGPIPE,SIGALRM,SIGTERM,0,SIGCHLD,SIGCONT,SIGSTOP,SIGTSTP,SIGTTIN,SIGTTOU};
    if(!n)return 0;
    for(int i=1;i<23;i++)if(host[i]&&host[i]==n)return i;
    if(n==SIGURG)return 23; if(n==SIGXCPU)return 24; if(n==SIGXFSZ)return 25;
    if(n==SIGVTALRM)return 26; if(n==SIGPROF)return 27; if(n==SIGWINCH)return 28;
    if(n==SIGIO)return 29; if(n==SIGSYS)return 31;
    return -1;
}
struct ProcessStdio {
    int child[3]={-1,-1,-1};
    int parent[3]={-1,-1,-1};
};
void CloseDescriptors(int (&descriptors)[3]) {
    for(int &fd:descriptors)if(fd>=0){close(fd);fd=-1;}
}
int CreateStdio(Local<Context> context,Local<Object> options,ProcessStdio &streams) {
    auto isolate=context->GetIsolate();
    auto value=Field(context,options,"stdio");
    if(!value->IsArray()||value.As<Array>()->Length()!=3)return UV_ENOSYS;
    auto array=value.As<Array>();
    for(int n=0;n<3;n++) {
        auto entry=array->Get(context,n).ToLocalChecked().As<Object>();
        auto type=Text(isolate,Field(context,entry,"type"));
        if(type=="pipe"&&!Field(context,entry,"ipc")->BooleanValue(isolate)) {
            int pair[2];
            if(pipe(pair))return uv_translate_sys_error(errno);
            streams.child[n]=pair[n==0?0:1]; streams.parent[n]=pair[n==0?1:0];
        } else if(type=="ignore") {
            streams.child[n]=open("/dev/null",n==0?O_RDONLY:O_WRONLY);
            if(streams.child[n]<0)return uv_translate_sys_error(errno);
        } else if(type=="fd"||type=="inherit") {
            int fd=Field(context,entry,"fd")->Int32Value(context).FromMaybe(-1);
            streams.child[n]=dup(fd);
            if(streams.child[n]<0)return uv_translate_sys_error(errno);
        } else return UV_ENOSYS;
    }
    return 0;
}
void Signal(const FunctionCallbackInfo<Value>& a) {
    auto context=a.GetIsolate()->GetCurrentContext();
    int pid=a[0]->Int32Value(context).FromMaybe(0);
    int signal=LinuxSignal(a[1]->Int32Value(context).FromMaybe(-1));
    uint32_t generation=a.Length()>3?a[3]->Uint32Value(context).FromMaybe(0):0;
    int result=UV_ESRCH;
    if(signal<0)result=UV_EINVAL;
    else if(pid>1) {
        int error=a[2]->BooleanValue(a.GetIsolate())?
            IMDreamGuestKillGroup(pid,signal,generation):IMDreamGuestKillProcess(pid,signal,generation);
        result=error<0?UV_ESRCH:0;
    }
    a.GetReturnValue().Set(Integer::New(a.GetIsolate(),result));
}
struct SynchronousProcess { std::atomic<int> status{-1}; };
void OnSyncExit(void *context,int status) {
    static_cast<SynchronousProcess *>(context)->status.store(status);
}
void SpawnSync(const FunctionCallbackInfo<Value>& a) {
    auto isolate=a.GetIsolate(); auto context=isolate->GetCurrentContext();
    auto options=a[0].As<Object>(); auto result=Object::New(isolate);
    ProcessStdio streams;
    int error=CreateStdio(context,options,streams), pipe_error=0, pid=0;
    SynchronousProcess process;
    uint32_t process_generation=0;
    auto args=Field(context,options,"args").As<Array>();
    auto file=Text(isolate,Field(context,options,"file"));
    auto cwd_value=Field(context,options,"cwd");
    auto cwd=Text(isolate,cwd_value);
    auto argv=Strings(context,args), env=Strings(context,Field(context,options,"envPairs").As<Array>());
    auto timeout_value=Field(context,options,"timeout"), maximum_value=Field(context,options,"maxBuffer");
    double timeout=timeout_value->IsNumber()?timeout_value->NumberValue(context).FromMaybe(0):0;
    double maximum=maximum_value->IsNumber()?maximum_value->NumberValue(context).FromMaybe(0):0;
    auto signal_value=Field(context,options,"killSignal");
    int signal=LinuxSignal(signal_value->IsInt32()?signal_value->Int32Value(context).FromJust():SIGTERM);
    if(signal<0)error=UV_EINVAL;
    if(!Field(context,options,"uid")->IsNullOrUndefined()||!Field(context,options,"gid")->IsNullOrUndefined())error=UV_ENOSYS;
    std::string input, captured[2];
    if(!error) {
        auto first=Field(context,options,"stdio").As<Array>()->Get(context,0).ToLocalChecked().As<Object>();
        auto value=Field(context,first,"input");
        if(node::Buffer::HasInstance(value))input.assign(node::Buffer::Data(value),node::Buffer::Length(value));
        for(int fd:streams.parent)if(fd>=0&&fcntl(fd,F_SETFL,fcntl(fd,F_GETFL)|O_NONBLOCK)<0)error=uv_translate_sys_error(errno);
    }
    bool started=false;
    auto beginning=std::chrono::steady_clock::now();
    if(!error) {
        int status=IMDreamGuestSpawn(file.c_str(),args->Length(),argv.data(),argv.size(),env.data(),env.size(),cwd.c_str(),streams.child,OnSyncExit,&process,&pid,&process_generation);
        for(int &fd:streams.child)fd=-1; // Ownership passed to the guest, including failed exec.
        if(status<0)error=GuestError(status); else started=true;
    }
    CloseDescriptors(streams.child);
    size_t written=0, buffered=0;
    bool killed=false;
    if(streams.parent[0]>=0&&input.empty()){close(streams.parent[0]);streams.parent[0]=-1;}
    while(started) {
        bool open=false;
        for(int fd:streams.parent)if(fd>=0)open=true;
        if(process.status.load()>=0&&!open)break;
        double elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-beginning).count();
        if(!error&&!killed&&timeout>0&&elapsed>=timeout)error=UV_ETIMEDOUT;
        if(error&&!killed) {
            killed=true;
            if(process.status.load()<0)IMDreamGuestKillProcess(pid,signal,process_generation);
            CloseDescriptors(streams.parent);
        }
        // Polling only blocks this Node Worker; guest execution and the app's other Workers continue.
        pollfd ready[3];
        for(int n=0;n<3;n++)ready[n]={streams.parent[n],static_cast<short>(n==0?POLLOUT:POLLIN),0};
        int interval=10;
        if(!killed&&timeout>0&&timeout-elapsed<interval)interval=0;
        if(poll(ready,3,interval)<0) {
            if(errno==EINTR)continue;
            if(!error)error=uv_translate_sys_error(errno);
            continue;
        }
        for(int n=0;n<3;n++) {
            int fd=streams.parent[n];
            if(fd<0||!ready[n].revents)continue;
            if(n==0) {
                ssize_t count=write(fd,input.data()+written,input.size()-written);
                if(count>0)written+=count;
                else if(count<0&&errno!=EAGAIN&&errno!=EINTR){if(!pipe_error)pipe_error=uv_translate_sys_error(errno);}
                if(pipe_error||written==input.size()){close(fd);streams.parent[n]=-1;}
            } else {
                char bytes[16384];
                ssize_t count=read(fd,bytes,sizeof(bytes));
                if(count>0) {
                    captured[n-1].append(bytes,count); buffered+=count;
                    if(!error&&maximum>0&&buffered>maximum)error=UV_ENOBUFS;
                } else if(!count||(errno!=EAGAIN&&errno!=EINTR)) {
                    if(count<0&&!pipe_error)pipe_error=uv_translate_sys_error(errno);
                    close(fd); streams.parent[n]=-1;
                }
            }
        }
    }
    CloseDescriptors(streams.parent);
    if(!error)error=pipe_error;
    if(error)Set(context,result,"error",Integer::New(isolate,error));
    int status=process.status.load(), exit_signal=started?status&0x7f:0;
    Set(context,result,"pid",Integer::New(isolate,pid));
    Set(context,result,"generation",Integer::NewFromUnsigned(isolate,process_generation));
    Set(context,result,"status",started&&!exit_signal?Local<Value>(Integer::New(isolate,(status>>8)&0xff)):Local<Value>(Null(isolate)));
    Set(context,result,"signal",exit_signal?Local<Value>(Key(isolate,SignalName(exit_signal))):Local<Value>(Null(isolate)));
    if(!started)Set(context,result,"output",Null(isolate));
    else {
        auto output=Array::New(isolate,3);
        output->Set(context,0,Null(isolate)).Check();
        auto entries=Field(context,options,"stdio").As<Array>();
        for(int n=1;n<3;n++) {
            auto entry=entries->Get(context,n).ToLocalChecked().As<Object>();
            Local<Value> bytes=Null(isolate);
            if(Text(isolate,Field(context,entry,"type"))=="pipe")
                bytes=node::Buffer::Copy(isolate,captured[n-1].data(),captured[n-1].size()).ToLocalChecked();
            output->Set(context,n,bytes).Check();
        }
        Set(context,result,"output",output);
    }
    a.GetReturnValue().Set(result);
}
void Dispose(uv_handle_t *h) {
    auto p=static_cast<NodeProcess *>(h->data);
    // A queued uv notification may run while the guest thread is still returning from uv_async_send.
    { std::lock_guard<std::mutex> completed(p->exitMutex); }
    auto done=p->cleanupDone; auto context=p->cleanupContext;
    if(p->cleanup)node::RemoveEnvironmentCleanupHook(std::move(p->cleanup));
    delete p->resource; p->callback.Reset(); p->context.Reset(); delete p;
    if(done)done(context);
}
void CleanupProcess(void *context,void (*done)(void *),void *doneContext) {
    auto p=static_cast<NodeProcess *>(context);
    p->closing=true; p->cleanupDone=done; p->cleanupContext=doneContext;
    uv_ref(reinterpret_cast<uv_handle_t *>(&p->notification));
    IMDreamGuestKillGroup(p->pid,9,p->generation);
    if(p->status.load()>=0&&!uv_is_closing(reinterpret_cast<uv_handle_t *>(&p->notification)))
        uv_close(reinterpret_cast<uv_handle_t *>(&p->notification),Dispose);
}
void Notify(uv_async_t *h) {
    auto p=static_cast<NodeProcess *>(h->data);
    if(p->closing) {
        if(!uv_is_closing(reinterpret_cast<uv_handle_t *>(h)))uv_close(reinterpret_cast<uv_handle_t *>(h),Dispose);
        return;
    }
    auto i=p->isolate;
    HandleScope scope(i); auto c=p->context.Get(i); Context::Scope context_scope(c);
    int status=p->status.load(), signal=status&0x7f;
    Local<Value> values[]={Integer::New(i,signal?0:(status>>8)&0xff),signal?Local<Value>(Key(i,SignalName(signal))):Local<Value>(Null(i))};
    auto result=p->resource->MakeCallback(p->callback.Get(i),2,values); (void)result;
}
void OnExit(void *context,int status) {
    auto p=static_cast<NodeProcess *>(context);
    std::lock_guard<std::mutex> completed(p->exitMutex);
    p->status.store(status); uv_async_send(&p->notification);
}
NodeProcess *Handle(const FunctionCallbackInfo<Value>& a) { return static_cast<NodeProcess *>(a[0].As<External>()->Value()); }
void HostPID(const FunctionCallbackInfo<Value>& a) { a.GetReturnValue().Set(Integer::New(a.GetIsolate(),getpid())); }
void InitializeGuest(const FunctionCallbackInfo<Value>& a) {
    a.GetReturnValue().Set(Integer::New(a.GetIsolate(),IMDreamGuestInitialize(Text(a.GetIsolate(),a[0]).c_str(),Text(a.GetIsolate(),a[1]).c_str(),Text(a.GetIsolate(),a[2]).c_str())));
}
void Spawn(const FunctionCallbackInfo<Value>& a) {
    auto i=a.GetIsolate(); auto c=i->GetCurrentContext(); auto input=a[0].As<Object>(); auto result=Object::New(i);
    ProcessStdio streams;
    int stdio_error=CreateStdio(c,input,streams);
    if(stdio_error) {
        CloseDescriptors(streams.child); CloseDescriptors(streams.parent);
        Set(c,result,"error",Integer::New(i,stdio_error)); a.GetReturnValue().Set(result); return;
    }
    auto p=new NodeProcess; p->isolate=i; p->context.Reset(i,c); p->callback.Reset(i,a[1].As<Function>());
    p->resource=new node::AsyncResource(i,Object::New(i),"ink:guestProcess");
    int notification_error=uv_async_init(node::GetCurrentEventLoop(i),&p->notification,Notify);
    if(notification_error) {
        CloseDescriptors(streams.child); CloseDescriptors(streams.parent);
        delete p->resource; p->callback.Reset(); p->context.Reset(); delete p;
        Set(c,result,"error",Integer::New(i,notification_error)); a.GetReturnValue().Set(result); return;
    }
    p->notification.data=p;
    auto file=Text(i,Field(c,input,"file")), cwd=Text(i,Field(c,input,"cwd"));
    auto argv=Field(c,input,"args").As<Array>(); auto argv_bytes=Strings(c,argv), env=Strings(c,Field(c,input,"envPairs").As<Array>());
    int started=IMDreamGuestSpawn(file.c_str(),argv->Length(),argv_bytes.data(),argv_bytes.size(),env.data(),env.size(),cwd.c_str(),streams.child,OnExit,p,&p->pid,&p->generation);
    if(started<0) {
        CloseDescriptors(streams.parent);
        p->closing=true; uv_close(reinterpret_cast<uv_handle_t *>(&p->notification),Dispose);
        Set(c,result,"error",Integer::New(i,GuestError(started)));
    } else {
        p->cleanup=node::AddEnvironmentCleanupHook(i,CleanupProcess,p);
        Set(c,result,"pid",Integer::New(i,p->pid)); Set(c,result,"generation",Integer::NewFromUnsigned(i,p->generation)); Set(c,result,"handle",External::New(i,p));
        auto descriptors=Array::New(i,3);
        for(int n=0;n<3;n++)descriptors->Set(c,n,Integer::New(i,streams.parent[n])).Check();
        Set(c,result,"fds",descriptors);
    }
    a.GetReturnValue().Set(result);
}
void Close(const FunctionCallbackInfo<Value>& a) {
    auto p=Handle(a); p->closing=true;
    if(p->status.load()<0)IMDreamGuestKillGroup(p->pid,9,p->generation);
    else if(!uv_is_closing(reinterpret_cast<uv_handle_t *>(&p->notification)))uv_close(reinterpret_cast<uv_handle_t *>(&p->notification),Dispose);
}
void Kill(const FunctionCallbackInfo<Value>& a) {
    auto p=Handle(a); int signal=LinuxSignal(a[1]->Int32Value(a.GetIsolate()->GetCurrentContext()).FromMaybe(-1));
    int result=signal<0?UV_EINVAL:IMDreamGuestKillProcess(p->pid,signal,p->generation);
    a.GetReturnValue().Set(Integer::New(a.GetIsolate(),signal<0?UV_EINVAL:result<0?UV_ESRCH:0));
}
void Reference(const FunctionCallbackInfo<Value>& a) {
    auto h=reinterpret_cast<uv_handle_t *>(&Handle(a)->notification);
    if(a[1]->BooleanValue(a.GetIsolate()))uv_ref(h); else uv_unref(h);
}
void Initialize(Local<Object> exports,Local<Value>,Local<Context> context) {
    NODE_SET_METHOD(exports,"hostPID",HostPID); NODE_SET_METHOD(exports,"initialize",InitializeGuest);
    NODE_SET_METHOD(exports,"spawn",Spawn); NODE_SET_METHOD(exports,"close",Close);
    NODE_SET_METHOD(exports,"kill",Kill); NODE_SET_METHOD(exports,"reference",Reference);
    NODE_SET_METHOD(exports,"spawnSync",SpawnSync); NODE_SET_METHOD(exports,"signal",Signal);
    Set(context,exports,"version",Integer::New(context->GetIsolate(),1));
}
NODE_MODULE_LINKED(ink_dream_process,Initialize)
}
