import type { Backend } from "./backend";
import { createExampleBackend } from "./example/server";
import { createSupabaseBackend } from "./supabase";

/**
 * Com VITE_SUPABASE_URL e VITE_SUPABASE_ANON_KEY (chave pública), o site usa o
 * serviço real. Sem elas, abre no modo EXEMPLO, sempre identificado na tela.
 */
export function createBackend(): Backend {
  const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (url || key) {
    if (!url || !key) throw new Error("Informe o endereço e a chave pública do serviço.");
    return createSupabaseBackend(url, key);
  }
  return createExampleBackend();
}
