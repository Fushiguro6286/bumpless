import { Empty } from "../components/ui";

export default function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <Empty>{note}</Empty>
    </div>
  );
}
