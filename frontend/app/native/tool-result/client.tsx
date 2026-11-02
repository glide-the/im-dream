'use client';
// [Input] Original DOM-only tool and MCP App dependencies.
// [Output] Client-only local tool document.
// [Pos] Next initialization boundary; third-party packages retain their original source.
import dynamic from 'next/dynamic';
const ToolResultDocument=dynamic(()=>import('../../_dream/components/chat/ToolResultDocument'),{ssr:false});
export default ToolResultDocument;
