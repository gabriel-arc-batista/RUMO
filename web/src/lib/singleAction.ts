import { uuid } from "./ids";

/** One confirmed action per rendered item; retries keep the original event ID. */
export class SingleAction {
  private entries = new Map<string, { id: string; promise?: Promise<void> }>();

  run(key: string, action: (id: string) => Promise<void>): Promise<void> {
    const entry = this.entries.get(key) ?? { id: uuid() };
    if (entry.promise) return entry.promise;
    this.entries.set(key, entry);
    // Defer execution until the promise has been installed: synchronous repeat
    // calls, mouse and keyboard all observe the same in-flight operation.
    entry.promise = Promise.resolve().then(() => action(entry.id)).catch((error) => {
      entry.promise = undefined;
      throw error;
    });
    return entry.promise;
  }
}
