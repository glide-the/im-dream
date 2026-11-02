// [Input] Fixed local diagram document route.
// [Output] Existing Mermaid presentation; native owns Chat and navigation.
// [Pos] Next document leaf consumed by MermaidBlock.native.
import type {Metadata} from 'next';
import MermaidClient from './client';
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function MermaidPage(){return <MermaidClient/>;}
