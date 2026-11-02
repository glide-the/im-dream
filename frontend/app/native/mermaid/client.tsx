'use client';
// [Input] Original browser-only Mermaid renderer and local diagram protocol.
// [Output] Client-only Mermaid document.
// [Pos] Next initialization boundary; Mermaid package source remains unchanged.
import dynamic from 'next/dynamic';
export default dynamic(()=>import('../../_dream/components/chat/MermaidDocument'),{ssr:false});
