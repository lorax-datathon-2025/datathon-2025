// Dashboard.tsx
import React, { useMemo, useState } from "react";
import { FileText, CheckCircle, AlertTriangle, Lock, Eye, Search as SearchIcon, MoreHorizontal, Download, ShieldAlert, Users, Gauge } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { motion } from "framer-motion";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/* ------------------------ mock data ------------------------ */
type DocRow = {
  id: string;
  name: string;
  classification: "Public" | "Confidential" | "Highly Sensitive" | "Unsafe";
  pages: number;
  images: number;
  unsafe: boolean;
  needsReview: boolean;
  confidence: number; // 0–100
  uploadedAt: string;
};

const mock: DocRow[] = [
  { id: "TC1", name: "Marketing Brochure Q4 2024.pdf", classification: "Public", pages: 12, images: 8, unsafe: false, needsReview: false, confidence: 98, uploadedAt: "2024-01-15" },
  { id: "TC2", name: "Employment Application - John Doe.pdf", classification: "Highly Sensitive", pages: 5, images: 1, unsafe: false, needsReview: true, confidence: 95, uploadedAt: "2024-01-14" },
  { id: "TC3", name: "Internal Project Memo.docx", classification: "Confidential", pages: 3, images: 0, unsafe: false, needsReview: false, confidence: 92, uploadedAt: "2024-01-13" },
  { id: "TC4", name: "Stealth Fighter.jpeg", classification: "Confidential", pages: 1, images: 1, unsafe: false, needsReview: true, confidence: 86, uploadedAt: "2024-01-12" },
  { id: "TC5", name: "Mixed Content – Fighter + Unsafe.docx", classification: "Unsafe", pages: 7, images: 4, unsafe: true, needsReview: true, confidence: 80, uploadedAt: "2024-01-12" },
];

/* ------------------------ helpers ------------------------ */
const categoryBadge = (c: DocRow["classification"]) => {
  switch (c) {
    case "Public":
      return { className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20", icon: <CheckCircle className="h-3.5 w-3.5" /> };
    case "Confidential":
      return { className: "bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/20", icon: <Eye className="h-3.5 w-3.5" /> };
    case "Highly Sensitive":
      return { className: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/20", icon: <Lock className="h-3.5 w-3.5" /> };
    case "Unsafe":
      return { className: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/20", icon: <AlertTriangle className="h-3.5 w-3.5" /> };
  }
};

const Dot = ({ ok, label }: { ok: boolean; label?: string }) => (
  <div className="inline-flex items-center gap-2">
    <span className={`h-2.5 w-2.5 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`} />
    {label && <span className="text-sm text-muted-foreground">{label}</span>}
  </div>
);

const float = (delay = 0): any => ({
  initial: { opacity: 0, y: 12, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1, transition: { delay, duration: 0.5, ease: "easeOut" } },
});

function avgConfidence(rows: { confidence: number }[]) {
  if (!rows.length) return 0;
  const sum = rows.reduce((a, b) => a + b.confidence, 0);
  return Math.round((sum / rows.length) * 10) / 10; // one decimal
}


/* ------------------------ component ------------------------ */
const Dashboard: React.FC = () => {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<"All" | DocRow["classification"]>("All");
  const [show, setShow] = useState<"All" | "Unsafe" | "NeedsReview">("All");

  const stats = useMemo(() => {
    const total = mock.length;
    return {
      total,
      public: mock.filter((d) => d.classification === "Public").length,
      confidential: mock.filter((d) => d.classification === "Confidential").length,
      sensitive: mock.filter((d) => d.classification === "Highly Sensitive").length,
      unsafe: mock.filter((d) => d.classification === "Unsafe").length,
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return mock.filter((d) => {
      if (category !== "All" && d.classification !== category) return false;
      if (show === "Unsafe" && !d.unsafe) return false;
      if (show === "NeedsReview" && !d.needsReview) return false;
      if (q && !`${d.id} ${d.name}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [query, category, show]);

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="absolute inset-x-0 top-0 z-0 h-[420px] overflow-hidden" style={{ clipPath: "polygon(0 0, 100% 0, 100% 85%, 0 100%)" }}>
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(1000px 500px at -5% -5%, rgba(52,211,153,.55), transparent 50%), radial-gradient(1000px 600px at 110% 8%, rgba(139,92,246,.5), transparent 50%), radial-gradient(700px 380px at 40% 18%, rgba(236,72,153,.5), transparent 50%), linear-gradient(120deg, #10b981 0%, #8b5cf6 35%, #ec4899 70%)",
            opacity: 0.7,
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.06] mix-blend-overlay"
          style={{
            backgroundImage:
              'url("data:image/svg+xml,%3Csvg width=\'160\' height=\'160\' viewBox=\'0 0 40 40\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23000000\'%3E%3Ccircle cx=\'1\' cy=\'1\' r=\'.7\'/%3E%3C/g%3E%3C/svg%3E")',
          }}
        />
      </div>


      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute -top-24 right-[10%] h-96 w-96 rounded-full bg-purple-500/20 blur-3xl" />
        <div className="absolute top-[40%] -left-24 h-80 w-80 rounded-full bg-emerald-500/20 blur-3xl" />
        <div className="absolute bottom-[20%] right-[30%] h-72 w-72 rounded-full bg-fuchsia-500/20 blur-3xl" />
      </div>

  <div className="container relative z-10 mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8 flex flex-wrap items-center justify-between gap-3"
        >
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-neutral-900 dark:text-neutral-100">Document Dashboard</h1>
            <p className="mt-2 text-lg text-neutral-600 dark:text-neutral-400">Recent analyses with category, counts, safety, HITL and actions</p>
          </div>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}>
            <Button variant="default" className="gap-2 rounded-full bg-neutral-900 px-6 py-3 font-semibold text-white shadow-lg hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100">
              <Download className="h-4 w-4" /> Download CSV
            </Button>
          </motion.div>
        </motion.div>

        {/* Stat cards — animated & on-brand */}
<div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
  {/* Flagged documents */}
  <motion.div
    {...float(0.05)}
    className="relative overflow-hidden rounded-2xl border border-rose-500/20 bg-white/80 p-5 shadow-sm dark:border-rose-500/20 dark:bg-neutral-900/70"
  >
    <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-rose-500/10 blur-2xl" />
    <div className="flex items-center justify-between">
      <div>
        <div className="text-xs font-medium text-rose-600">Flagged</div>
        <div className="mt-1 text-3xl font-bold text-rose-700 dark:text-rose-400">
          {mock.filter((d) => d.unsafe).length}
        </div>
      </div>
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-500/15">
        <AlertTriangle className="h-5 w-5 text-rose-600" />
      </div>
    </div>
    <div className="mt-3 text-xs text-muted-foreground">Unsafe content requiring attention</div>
  </motion.div>

  {/* Needs review (HITL) */}
  <motion.div
    {...float(0.1)}
    className="relative overflow-hidden rounded-2xl border border-fuchsia-500/20 bg-white/80 p-5 shadow-sm dark:border-fuchsia-500/20 dark:bg-neutral-900/70"
  >
    <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-fuchsia-500/10 blur-2xl" />
    <div className="flex items-center justify-between">
      <div>
        <div className="text-xs font-medium text-fuchsia-600">Needs review</div>
        <div className="mt-1 text-3xl font-bold text-fuchsia-700 dark:text-fuchsia-400">
          {mock.filter((d) => d.needsReview).length}
        </div>
      </div>
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-fuchsia-500/15">
        <Users className="h-5 w-5 text-fuchsia-600" />
      </div>
    </div>
    <div className="mt-3 text-xs text-muted-foreground">Queued for SME HITL validation</div>
  </motion.div>

  {/* Average confidence */}
  <motion.div
    {...float(0.15)}
    className="relative overflow-hidden rounded-2xl border border-indigo-500/20 bg-white/80 p-5 shadow-sm dark:border-indigo-500/20 dark:bg-neutral-900/70"
  >
    <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-indigo-500/10 blur-2xl" />
    <div className="flex items-center justify-between">
      <div>
        <div className="text-xs font-medium text-indigo-600">Average confidence</div>
        <div className="mt-1 flex items-baseline gap-2">
          <div className="text-3xl font-bold text-indigo-700 dark:text-indigo-400">
            {avgConfidence(mock)}%
          </div>
        </div>
      </div>
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/15">
        <Gauge className="h-5 w-5 text-indigo-600" />
      </div>
    </div>
    {/* subtle progress bar */}
    <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
      <motion.div
        className="h-full bg-indigo-500"
        initial={{ width: 0 }}
        animate={{ width: `${avgConfidence(mock)}%` }}
        transition={{ duration: 0.7, ease: "easeOut", delay: 0.2 }}
      />
    </div>
    <div className="mt-2 text-xs text-muted-foreground">Model agreement across recent docs</div>
  </motion.div>
</div>


        {/* Filters */}
        <motion.div {...float(0.2)}>
          <Card className="mb-6 border-white/30 bg-white/80 p-5 shadow-lg backdrop-blur-md dark:border-neutral-800 dark:bg-neutral-900/70">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by name or ID…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-64 rounded-xl border-neutral-200/70 pl-9 backdrop-blur dark:border-neutral-700"
                />
              </div>

              <Select value={category} onValueChange={(v: any) => setCategory(v)}>
                <SelectTrigger className="w-48 rounded-xl border-neutral-200/70 backdrop-blur dark:border-neutral-700">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">All categories</SelectItem>
                  <SelectItem value="Public">Public</SelectItem>
                  <SelectItem value="Confidential">Confidential</SelectItem>
                  <SelectItem value="Highly Sensitive">Highly Sensitive</SelectItem>
                  <SelectItem value="Unsafe">Unsafe</SelectItem>
                </SelectContent>
              </Select>

              <Select value={show} onValueChange={(v: any) => setShow(v)}>
                <SelectTrigger className="w-48 rounded-xl border-neutral-200/70 backdrop-blur dark:border-neutral-700">
                  <SelectValue placeholder="Show" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All">Show: All</SelectItem>
                  <SelectItem value="Unsafe">Show: Unsafe only</SelectItem>
                  <SelectItem value="NeedsReview">Show: Needs human review</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </Card>
        </motion.div>

        {/* Table */}
        <motion.div {...float(0.25)}>
          <Card className="overflow-hidden rounded-2xl border-white/30 bg-white/80 shadow-xl backdrop-blur-md dark:border-neutral-800 dark:bg-neutral-900/70">
            <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[38%]">Document</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-center">Pages</TableHead>
                <TableHead className="text-center">Images</TableHead>
                <TableHead className="text-center">Unsafe</TableHead>
                <TableHead className="text-center">Needs review</TableHead>
                <TableHead className="text-center">Conf.</TableHead>
                <TableHead className="w-[60px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((d) => {
                const cat = categoryBadge(d.classification);
                return (
                  <TableRow key={d.id} className="hover:bg-muted/40">
                    <TableCell>
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          <FileText className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <div className="truncate font-medium">{d.name}</div>
                          <div className="text-xs text-muted-foreground">ID: {d.id} • {d.uploadedAt}</div>
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${cat.className}`}>
                        {cat.icon}
                        {d.classification}
                      </span>
                    </TableCell>

                    <TableCell className="text-center">{d.pages}</TableCell>
                    <TableCell className="text-center">{d.images}</TableCell>
                    <TableCell className="text-center">
                      <Dot ok={!d.unsafe} label={d.unsafe ? "Flagged" : "Clean"} />
                    </TableCell>
                    <TableCell className="text-center">
                      <Dot ok={!d.needsReview} label={d.needsReview ? "Required" : "OK"} />
                    </TableCell>
                    <TableCell className="text-center">{d.confidence}%</TableCell>

                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button size="icon" variant="ghost" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          <DropdownMenuItem className="gap-2">
                            <Eye className="h-4 w-4" /> View report
                          </DropdownMenuItem>
                          <DropdownMenuItem className="gap-2">
                            <ShieldAlert className="h-4 w-4" /> Send to HITL
                          </DropdownMenuItem>
                          <DropdownMenuItem className="gap-2">
                            <Download className="h-4 w-4" /> Export JSON
                          </DropdownMenuItem>
                          <DropdownMenuItem className="gap-2 text-rose-600 focus:text-rose-600">
                            <AlertTriangle className="h-4 w-4" /> Mark unsafe
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-10 text-center text-sm text-muted-foreground">
                    No documents match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;