import { LicenceWorkspace } from "./_components/LicenceWorkspace";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center bg-zinc-50 px-4 py-12 dark:bg-black sm:py-20">
      <header className="mb-8 max-w-xl text-center">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Driving Licence Reader</h1>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">
          Upload a driving licence to extract its details, review them, and ask questions about the
          document.
        </p>
      </header>
      <LicenceWorkspace />
    </main>
  );
}
