// [Input] Existing isolated Settings/AppState facade and the native Chat recovery fixture.
// [Output] Explicit iOS capability for the production Settings adapter in the browser harness.
// [Pos] Test-only platform boundary; no native runtime, account or provider is started.
export * from './session-platform-web-boundary';
export const Platform={OS:'ios',select:<T,>(values:{ios?:T;native?:T;default?:T})=>values.ios??values.native??values.default};
