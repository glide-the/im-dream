// [Input] Original language/energy preference keys and the iOS application Settings store.
// [Output] Native display preferences with the existing defaults and no account/session data.
// [Pos] Concrete iOS persistence adapter for the original General settings fields.
import {readInterfacePreference,writeInterfacePreference} from './interfaceSettings';
import i18n,{LANGUAGE_STORAGE_KEY} from '../../app/_dream/i18n';
export const INTERFACE_LANGUAGE_CODES=['en','zh'] as const;
const ENERGY_KEY='show-energy-bar';
export function initInterfaceLanguage():void {
  const language=readInterfacePreference(LANGUAGE_STORAGE_KEY);
  if(INTERFACE_LANGUAGE_CODES.some(code=>code===language))void i18n.changeLanguage(language as string);
}
export async function setInterfaceLanguage(language:string):Promise<void> {
  if(!INTERFACE_LANGUAGE_CODES.some(code=>code===language))throw new Error('INTERFACE_LANGUAGE_INVALID');
  writeInterfacePreference(LANGUAGE_STORAGE_KEY,language);await i18n.changeLanguage(language);
}
export function getShowEnergyBar():boolean {const value=readInterfacePreference(ENERGY_KEY);return value?value==='true':true;}
export function setShowEnergyBar(value:boolean):void {writeInterfacePreference(ENERGY_KEY,String(value));}
