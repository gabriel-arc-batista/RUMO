/** Browser-safe RPC transport. Never use a service-role credential here. */
export type SyncState = 'offline' | 'pending' | 'syncing' | 'synced' | 'conflict' | 'error';
export type Rating = 1 | 2 | 3 | 4;
export interface CardPayload { deck_id: string; front: string; back: string; explanation: string; source: string; lesson_id: string | null; question_id: string | null; suspended: boolean; deleted: boolean }
export interface Payloads {
  'reading.page': {lesson_id:string;version:string;page:number;pages:number;read:boolean};
  'reading.position': {lesson_id:string;version:string;page:number;pages:number};
  'note.save': {lesson_id:string|null;question_id?:string|null;version:string;page:number|null;text:string;deleted:boolean};
  'favorite.set': {target_type:string;target_id:string;version:string;favorite:boolean};
  'arena.attempt': {question_id:string;version:string;answer:string;session_id:string};
  'card.save': CardPayload;
  'card.review': {card_id:string;version:string;rating:Rating;session_id:string};
  'study.session': {plan_id:string;subject_id:string;topic_id:string|null;day:string;category:string;elapsed:number;lesson_id:string|null;lesson_version:string|null};
  /** Desktop → site (009): aparência, nome e IDs equipados; entidade "profile:character". */
  'profile.character': {name:string;look:Record<string,string>;equipped:string[]};
  /** Desktop → site (009): retrato somente leitura do ciclo ativo; entidade "cycle:current". */
  'cycle.snapshot': {plan_name:string;position:number;items:CycleItem[]};
}
export interface CycleItem {subject:string;topic:string|null;category:'Teoria'|'Questões'|'Revisão'|'Simulado';target_minutes:number;done:boolean}
export type EventKind = keyof Payloads;
export type EventEnvelope = { [K in EventKind]: {id:string;device_id:string;kind:K;entity_id:string;base_revision:number;payload:Payloads[K]} }[EventKind];
export type EventResult = {status?: 'correct'|'incorrect'|'annulled'; answer?:string; comment?:string; interval_days?:number; repetitions?:number; ease?:number; due_at?:string; xp?:number; coins?:number};
export type ServerEvent = EventEnvelope & {sequence:number;revision:number;received_at:string;result?:EventResult|null};
/** victories: questões (id+versão) distintas com acerto confirmado; não altera XP (009). */
export interface ProgressSummary {level:number;xp:number;xp_next:number;coins:number;look:Record<string,string>|null;name?:string|null;equipped?:string[];victories?:number}

export function validatePublicKey(value:string):void {
  if(!value || /[\x00-\x1f]/.test(value) || value.startsWith('sb_secret_')) throw new Error('Use somente a chave pública do serviço');
  const parts=value.split('.');
  if(parts.length===3) {
    let payload:unknown;
    try {payload=JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));} catch {return;}
    if(payload && typeof payload==='object' && 'role' in payload && ['service_role','supabase_admin'].includes(String(payload.role))) throw new Error('Use somente a chave pública do serviço');
  }
}

export class RumoApiError extends Error {
  constructor(public code:string, public status:number, message:string) {super(message);}
}
export class RumoApi {
  constructor(private url:string, private publicKey:string, private accessToken:()=>string|null) {
    validatePublicKey(publicKey);
    const parsed = new URL(url);
    if(parsed.username || parsed.password || parsed.search || parsed.hash || !['','/'].includes(parsed.pathname)) throw new Error('Origem do serviço inválida');
    if (parsed.protocol !== 'https:' && !(parsed.protocol === 'http:' && ['localhost','127.0.0.1'].includes(parsed.hostname))) throw new Error('HTTPS obrigatório');
  }
  private async rpc<T>(name:string, args:object):Promise<T> {
    const token=this.accessToken();
    if (!token) throw new RumoApiError('unauthenticated',401,'Entre na sua conta.');
    const response=await fetch(`${this.url.replace(/\/$/,'')}/rest/v1/rpc/${name}`,{method:'POST',headers:{'Content-Type':'application/json',apikey:this.publicKey,Authorization:`Bearer ${token}`},body:JSON.stringify(args),redirect:'error',signal:AbortSignal.timeout(15000)});
    const body=await response.text();
    if(body.length>16777216) throw new RumoApiError('invalid_response',response.status,'Resposta longa demais.');
    let data: any;
    try {data=JSON.parse(body);} catch {throw new RumoApiError('invalid_response',response.status,'Resposta inválida do serviço.');}
    if(!response.ok) throw new RumoApiError(data.message || data.code || 'error',response.status,data.message || 'Falha de sincronização.');
    return data as T;
  }
  pushEvents(events:EventEnvelope[]):Promise<{id:string;sequence:number}[]> {
    if(events.length>100) throw new Error('Até 100 eventos por envio.');
    return this.rpc('push_events',{events});
  }
  progressSummary():Promise<ProgressSummary> {return this.rpc('progress_summary',{});}
  questionCatalog(filters:{subject?:string;topic?:string;exam?:string;wrong_only?:boolean;favorite_only?:boolean;bank?:string;year?:number;difficulty?:string;batch_size?:number}={}):Promise<Record<string,unknown>[]> {return this.rpc('question_catalog',filters);}
  pullEvents(afterSequence:number,batchSize=200):Promise<ServerEvent[]> {return this.rpc('pull_events',{after_sequence:afterSequence,batch_size:batchSize});}
}
