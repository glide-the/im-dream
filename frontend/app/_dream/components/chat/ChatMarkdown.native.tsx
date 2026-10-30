// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-28: render original Workspace image/reference capabilities through native private-file leases and the bound Thread.
// [Sync] 2026-10-28: align each native Markdown table column to its widest measured cell; original Web table/CSS remain unchanged.
// [Input] Original Markdown/GFM text, current theme and caller-owned link/file navigation.
// [Output] Native text, lists, tables and code using the existing react-markdown/remark-gfm parser.
// [Pos] Markdown presentation adapter; original Web ChatMarkdown/CSS and third-party source remain unchanged.
import {Children,createContext,isValidElement,useCallback,useContext,useMemo,useRef,useState,type ReactNode} from 'react';
import {Image,ScrollView,StyleSheet,Text,View,useWindowDimensions,type TextProps,type TextStyle} from 'react-native';
import Markdown,{defaultUrlTransform,type Components,type ExtraProps} from 'react-markdown';
import remarkGfm from 'remark-gfm';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {isWorkspaceUri,resolveWorkspaceDocumentReference,WORKSPACE_URI_PREFIX} from './workspaceUri';
import WorkspaceImage from './WorkspaceImage.native';
import type {WorkspaceAvailability,WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
const plugins=[remarkGfm];
const ListContext=createContext(false);
const TextStyleContext=createContext<TextStyle>({fontSize:15.2,lineHeight:26.6});
const blockTags=new Set(['p','h1','h2','h3','h4','h5','h6','ul','ol','pre','blockquote','table','thead','tbody','tr','th','td','hr','div','section','img']);
type Node={type:string;value?:string;children?:Node[];tagName?:string;properties?:Record<string,unknown>};
// Native View cannot own bare formatting newlines; preserve literal root HTML as text.
function nativeRootText(){return (tree:unknown)=>{const root=tree as Node;root.children=root.children?.flatMap(node=>{
  if(node.type==='raw')return [{type:'element',tagName:'p',properties:{},children:[{type:'text',value:node.value ?? ''}]}];
  if(node.type==='text')return node.value?.trim()?[{type:'element',tagName:'p',properties:{},children:[node]}]:[];
  return [node];
});};}
const rehypePlugins=[nativeRootText];
function plain(children:ReactNode):string{return Children.toArray(children).map(child=>typeof child==='string'||typeof child==='number'?String(child):isValidElement<{children?:ReactNode}>(child)?plain(child.props.children):'').join('');}
function RichText({children,style,...props}:Omit<TextProps,'children'>&{children?:ReactNode}){
  return <Text {...props} style={style}>{Children.map(children,(child,index)=>typeof child==='string'||typeof child==='number'?<InkLabel key={index}>{String(child)}</InkLabel>:child)}</Text>;
}
function flow(children:ReactNode,textStyle?:TextStyle):ReactNode[]{
  const result:ReactNode[]=[];let inline:ReactNode[]=[];
  const flush=()=>{if(inline.some(child=>typeof child!=='string'||child.trim()))result.push(<RichText key={`text-${result.length}`} style={textStyle}>{inline}</RichText>);inline=[];};
  Children.toArray(children).forEach(child=>{const tag=isValidElement<ExtraProps>(child)?child.props.node?.tagName:undefined;if(tag&&blockTags.has(tag)){flush();result.push(child);}else inline.push(child);});flush();return result;
}
function ListItem({children,value}:{children?:ReactNode;value?:string|number|readonly string[]}){const ordered=useContext(ListContext),body=useContext(TextStyleContext);return <View style={styles.listItem}><InkLabel style={[styles.bullet,body]}>{ordered?`${value ?? 1}.`:'•'}</InkLabel><View style={styles.listBody}>{flow(children,body)}</View></View>;}
function List({children,ordered,start=1}:{children?:ReactNode;ordered:boolean;start?:number}){
  const items=Children.toArray(children).filter(child=>typeof child!=='string'||child.trim());
  return <ListContext.Provider value={ordered}><View style={styles.list}>{items.map((child,index)=>isValidElement<{value?:number}>(child)?<ListItem key={child.key ?? index} value={ordered?start+index:undefined}>{child.props && 'children' in child.props?child.props.children as ReactNode:null}</ListItem>:null)}</View></ListContext.Provider>;
}
type TableGeometry={widths:readonly number[];measure:(column:number,width:number)=>void};
const TableContext=createContext<TableGeometry|undefined>(undefined);
const TableColumn=createContext(0);
function MarkdownTable({children}:{children?:ReactNode}){
  const [widths,setWidths]=useState<readonly number[]>([]);
  const measure=useCallback((column:number,width:number)=>{
    const measured=Math.ceil(width);
    setWidths(current=>{if((current[column]??0)>=measured)return current;const next=[...current];next[column]=measured;return next;});
  },[]);
  const value=useMemo(()=>({widths,measure}),[widths,measure]);
  return <TableContext.Provider value={value}><ScrollView horizontal style={styles.table}><View role="table">{flow(children)}</View></ScrollView></TableContext.Provider>;
}
function MarkdownTableRow({children}:{children?:ReactNode}){
  return <View role="row" style={styles.row}>{Children.toArray(children).filter(isValidElement).map((child,index)=><TableColumn.Provider key={child.key??index} value={index}>{child}</TableColumn.Provider>)}</View>;
}
function MarkdownTableCell({children,header=false}:{children?:ReactNode;header?:boolean}){
  const table=useContext(TableContext),column=useContext(TableColumn),text=useContext(TextStyleContext),colors=useInkColors();
  return <RichText role={header?'columnheader':'cell'} selectable onLayout={({nativeEvent})=>table?.measure(column,nativeEvent.layout.width)} style={[text,styles.cell,{width:table?.widths[column],fontWeight:header?'600':'400',borderColor:colors['color-border-paper']}]}>{children}</RichText>;
}
function MarkdownImage({uri,alt}:{uri:string;alt?:string}){
  const {width}=useWindowDimensions();
  const [ratio,setRatio]=useState(1),[failed,setFailed]=useState(false);
  return failed?<RichText>{alt ?? ''}</RichText>:<Image key={uri} source={{uri}} accessibilityLabel={alt} resizeMode="contain"
    onLoad={({nativeEvent})=>{const {width:w,height:h}=nativeEvent.source;if(w>0&&h>0)setRatio(w/h);}} onError={()=>setFailed(true)}
    style={{width:Math.min(448,width-32),maxWidth:'100%',aspectRatio:ratio}}/>;
}
export interface NativeChatMarkdownProps{text:string;fontSize?:number;lineHeight?:number;color?:string;origin?:string;workspaceSessionId?:string;workspaceAvailability?:WorkspaceAvailability;workspaceResources?:WorkspaceResources;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;workspaceDocumentPath?:string;onOpenLink?:(url:string)=>void;onOpenWorkspace?:(uri:string)=>void;}
export default function ChatMarkdown({text,fontSize=15.2,lineHeight=26.6,color,origin,workspaceSessionId,workspaceAvailability='disabled',workspaceResources,workspaceDocumentPath,onOpenLink,onOpenWorkspace,onAddImageMaterial}:NativeChatMarkdownProps){
  const colors=useInkColors();
  const callbacks=useRef({onOpenLink,onOpenWorkspace,onAddImageMaterial});callbacks.current={onOpenLink,onOpenWorkspace,onAddImageMaterial};
  const canOpenLink=Boolean(onOpenLink),canOpenWorkspace=Boolean(onOpenWorkspace&&workspaceSessionId&&workspaceAvailability==='enabled'),canAddImageMaterial=Boolean(onAddImageMaterial);
  const bodyColor=color??colors['color-text-body'];
  const components=useMemo<Components>(()=>{
    const body={fontSize,lineHeight,color:bodyColor};
    const paragraph=({children}:{children?:ReactNode})=>Children.toArray(children).some(child=>isValidElement<ExtraProps>(child)&&child.props.node?.tagName==='img')?<View style={styles.paragraph}>{flow(children,body)}</View>:<RichText selectable style={[body,styles.paragraph]}>{children}</RichText>;
    const block=({children}:{children?:ReactNode})=><View style={styles.block}>{flow(children,body)}</View>;
    const heading=(scale:number)=>({children}:{children?:ReactNode})=><RichText accessibilityRole="header" selectable style={[body,{fontSize:fontSize*scale,lineHeight:lineHeight*scale,fontWeight:'600',marginTop:fontSize*1.2,marginBottom:fontSize*0.5}]}>{children}</RichText>;
    return {
      p:paragraph,div:block,section:block,h1:heading(2),h2:heading(1.5),h3:heading(1.17),h4:heading(1),h5:heading(0.83),h6:heading(0.67),
      strong:({children})=><RichText style={{fontWeight:'600',color:colors['color-text-primary']}}>{children}</RichText>,
      em:({children})=><RichText style={{fontStyle:'italic'}}>{children}</RichText>,del:({children})=><RichText style={{textDecorationLine:'line-through'}}>{children}</RichText>,
      br:()=> <Text>{'\n'}</Text>,sup:({children})=><RichText style={{fontSize:fontSize*0.75}}>{children}</RichText>,
      ul:({children})=><List ordered={false}>{children}</List>,ol:({children,start})=><List ordered start={start}>{children}</List>,li:ListItem,
      input:({checked})=><Text accessibilityLabel={checked?'Checked':'Unchecked'}>{checked?'☑ ':'☐ '}</Text>,
      blockquote:({children})=><View style={[styles.quote,{borderLeftColor:colors['color-state-warning'],backgroundColor:colors['color-bg-surface']}]}>{flow(children,body)}</View>,
      hr:()=> <View style={{height:1,backgroundColor:colors['color-border-paper'],marginVertical:fontSize*0.9}} />,
      code:({children})=><Text selectable style={{fontFamily:'Menlo',fontSize:fontSize*0.92,color:colors['color-text-primary'],backgroundColor:colors['color-code-inline-bg']}}>{plain(children)}</Text>,
      pre:({children})=><ScrollView horizontal style={[styles.code,{backgroundColor:colors['color-code-bg']}]} contentContainerStyle={{padding:fontSize}}><Text selectable style={{fontFamily:'Menlo',fontSize:fontSize*0.92,lineHeight,color:colors['color-code-text']}}>{plain(children)}</Text></ScrollView>,
      a:({href,children})=>{const workspace=isWorkspaceUri(href),enabled=Boolean(href&&!href.startsWith('#')&&(workspace?canOpenWorkspace:canOpenLink));return <RichText accessibilityRole="link" aria-disabled={!enabled} accessibilityState={{disabled:!enabled}} onPress={enabled&&href?()=>{(workspace?callbacks.current.onOpenWorkspace:callbacks.current.onOpenLink)?.(href);}:undefined} style={{color:colors['color-action-link'],textDecorationLine:'underline'}}>{children}</RichText>;},
      img:({src,alt})=>{if(typeof src==='string'&&src.startsWith(WORKSPACE_URI_PREFIX))return <WorkspaceImage uri={src} alt={alt} threadId={workspaceSessionId} availability={workspaceAvailability} resources={workspaceResources} onAddImageMaterial={canAddImageMaterial?file=>callbacks.current.onAddImageMaterial!(file):undefined}/>;let uri:string|undefined;if(typeof src==='string'&&src.length>0){try{uri=new URL(src,origin).href;}catch{}}return uri?<MarkdownImage key={uri} uri={uri} alt={alt}/>:<RichText>{alt ?? ''}</RichText>;},
      table:MarkdownTable,thead:block,tbody:block,tr:MarkdownTableRow,
      th:({children})=><MarkdownTableCell header>{children}</MarkdownTableCell>,td:MarkdownTableCell,
    };
  },[fontSize,lineHeight,bodyColor,colors,origin,canOpenLink,canOpenWorkspace,workspaceSessionId,workspaceAvailability,workspaceResources,canAddImageMaterial]);
  return <TextStyleContext.Provider value={{fontSize,lineHeight,color:bodyColor}}><View style={{minWidth:0}}><Markdown remarkPlugins={plugins} rehypePlugins={rehypePlugins} components={components}
    urlTransform={value=>{const resolved=resolveWorkspaceDocumentReference(value,workspaceDocumentPath);return isWorkspaceUri(resolved)?resolved:defaultUrlTransform(resolved);}}>{text}</Markdown></View></TextStyleContext.Provider>;
}
const styles=StyleSheet.create({block:{minWidth:0},paragraph:{marginBottom:13.68},list:{marginBottom:13.68,gap:3.8},listItem:{flexDirection:'row',alignItems:'flex-start',gap:8,marginBottom:3.8},bullet:{fontSize:15.2,lineHeight:26.6,minWidth:16},listBody:{flex:1,minWidth:0},quote:{borderLeftWidth:4,paddingVertical:11.4,paddingHorizontal:15.2,marginBottom:13.68},code:{maxWidth:'100%',marginBottom:13.68,borderRadius:5.6},table:{maxWidth:'100%',marginBottom:13.68},row:{flexDirection:'row'},cell:{paddingVertical:6.4,paddingHorizontal:12,borderWidth:1,minWidth:80,maxWidth:300}});
