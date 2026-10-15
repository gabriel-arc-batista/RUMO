/** Inclusive PostgREST ranges. Continue to an empty page, even if a server
 * caps a response below the requested size. Never silently truncate a bank. */
export async function collectPages<T>(
  fetchPage: (from: number, to: number) => PromiseLike<{ data: T[] | null; error: unknown }>,
  size = 500,
): Promise<T[]> {
  if (!Number.isInteger(size) || size < 1) throw new Error("Tamanho de página inválido.");
  const rows: T[] = [];
  for (;;) {
    const { data, error } = await fetchPage(rows.length, rows.length + size - 1);
    if (error) throw error;
    if (!data?.length) return rows;
    rows.push(...data);
  }
}
