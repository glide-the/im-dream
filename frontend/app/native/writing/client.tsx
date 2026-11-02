'use client';
// [Input] Browser-only original Writing engine and canvas.
// [Output] Client-only local editor document mount.
// [Pos] Next boundary; DOM initialization runs after the document loads.
import dynamic from 'next/dynamic';
const WritingDocument=dynamic(()=>import('../../_dream/components/Editor/WritingDocument'),{ssr:false});
export default WritingDocument;
