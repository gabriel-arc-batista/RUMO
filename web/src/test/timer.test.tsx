import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const identity = vi.hoisted(() => ({ userId: "timer-a", mode: "exemplo" }));
vi.mock("../service/store", () => ({ useRumo: () => ({ account: { userId: identity.userId }, backend: { mode: identity.mode } }) }));
import { useStudyTimer } from "../components/StudyTimer";
const storage = (user = identity.userId) => `rumo.timer.exemplo:${user}:test`;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-12T12:00:00Z"));
  identity.userId = "timer-a";
  localStorage.clear();
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("tempo líquido por conta", () => {
  it("recupera pausado sem contar a ausência de uma execução antiga", () => {
    localStorage.setItem(storage(), JSON.stringify({ id: "old", seconds: 30, runningSince: Date.now() - 3_600_000 }));
    const { result } = renderHook(() => useStudyTimer("test"));
    expect(result.current.elapsed).toBe(30);
    expect(result.current.running).toBe(false);
  });

  it("conta só tempo iniciado, cria checkpoints pausados e restaura sem ausência", () => {
    const first = renderHook(() => useStudyTimer("test"));
    act(() => first.result.current.start());
    act(() => vi.advanceTimersByTime(6_000));
    expect(first.result.current.elapsed).toBe(6);
    const stored = JSON.parse(localStorage.getItem(storage())!);
    expect(stored.seconds).toBe(5);
    expect(stored.runningSince).toBeNull();
    first.unmount();
    act(() => vi.advanceTimersByTime(3_600_000));
    const reopened = renderHook(() => useStudyTimer("test"));
    expect(reopened.result.current.elapsed).toBe(6);
    expect(reopened.result.current.running).toBe(false);
  });

  it("trocar de conta não herda tempo nem ID da sessão anterior", () => {
    const a = renderHook(() => useStudyTimer("test"));
    act(() => a.result.current.start());
    act(() => vi.advanceTimersByTime(6_000));
    const oldId = a.result.current.sessionId;
    a.unmount();
    identity.userId = "timer-b";
    const b = renderHook(() => useStudyTimer("test"));
    expect(b.result.current.elapsed).toBe(0);
    expect(b.result.current.sessionId).not.toBe(oldId);
    expect(JSON.parse(localStorage.getItem(storage("timer-a"))!).seconds).toBe(6);
  });

  it("reset mantém a nova sessão no disco mesmo após limpar o efeito antigo", () => {
    const { result, unmount } = renderHook(() => useStudyTimer("test"));
    act(() => result.current.start());
    act(() => vi.advanceTimersByTime(6_000));
    const oldId = result.current.sessionId;
    act(() => result.current.reset());
    const stored = JSON.parse(localStorage.getItem(storage())!);
    expect(stored.seconds).toBe(0);
    expect(stored.id).not.toBe(oldId);
    unmount();
    expect(JSON.parse(localStorage.getItem(storage())!).id).toBe(stored.id);
  });

  it("suspensão longa pausa antes de somar a ausência", () => {
    const { result } = renderHook(() => useStudyTimer("test"));
    act(() => result.current.start());
    act(() => vi.advanceTimersByTime(3_000));
    vi.setSystemTime(Date.now() + 3_600_000);
    act(() => vi.advanceTimersByTime(1_000));
    expect(result.current.elapsed).toBe(3);
    expect(result.current.running).toBe(false);
    expect(result.current.autoPaused).toBe(true);
  });
});
