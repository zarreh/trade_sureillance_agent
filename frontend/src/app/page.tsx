import { RunConsole } from "@/components/RunConsole";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl p-8 font-sans">
      <h1 className="text-2xl font-bold">Trade Surveillance Agent</h1>
      <p className="mt-2 text-sm text-neutral-500">
        A grounded insider-trading investigation, streamed node-by-node. Every
        published finding is judged against the evidence before you see it —
        see{" "}
        <a className="underline" href="https://github.com/zarreh/trade_sureillance_agent">
          docs/how-it-works/grounding.md
        </a>{" "}
        for how.
      </p>

      <div className="mt-6">
        <RunConsole />
      </div>
    </main>
  );
}

