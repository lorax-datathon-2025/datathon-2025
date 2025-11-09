// Home.tsx
import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Shield,
  FileText,
  Image as ImageIcon,
  Video,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Users,
  Search,
  Lock,
  GitBranch,
} from "lucide-react";

// logo assets
import hitachiLogo from "../assets/hitachi.svg";
import geminiLogo from "../assets/gemini.svg";
import databricksLogo from "../assets/databricks.svg";

/* ---------- motion helpers  ---------- */
const fade = (d = 0): any => ({
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut", delay: d } },
  viewport: { once: true, amount: 0.4 },
});
const float = (delay = 0): any => ({
  animate: { y: [0, -8, 0], transition: { repeat: Infinity, duration: 4, delay, ease: "easeInOut" } },
});
const staggerParent: any = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const staggerItem: any = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

/* ---------- hero bg ---------- */
const HeroGradientBg: React.FC = () => (
  <div className="absolute inset-x-0 top-0 -z-10 h-[660px] overflow-hidden" style={{ clipPath: "polygon(0 0, 100% 0, 100% 85%, 0 100%)" }}>
    <div
      className="absolute inset-0"
      style={{
        background:
          "radial-gradient(1200px 600px at -10% -10%, rgba(52,211,153,.55), transparent 55%), radial-gradient(1200px 700px at 110% 10%, rgba(139,92,246,.55), transparent 55%), radial-gradient(900px 500px at 40% 20%, rgba(236,72,153,.55), transparent 55%), linear-gradient(120deg, #10b981 0%, #8b5cf6 35%, #ec4899 70%)",
      }}
    />
    <div
      className="absolute inset-0 opacity-[0.06] mix-blend-overlay"
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg width='160' height='160' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23000000'%3E%3Ccircle cx='1' cy='1' r='.7'/%3E%3C/g%3E%3C/svg%3E\")",
      }}
    />
  </div>
);

/* angled white slice under the gradient */
const SlantedDivider: React.FC = () => (
  <div
    className="pointer-events-none absolute inset-x-0 top-[560px] -z-10 h-[200px] bg-white dark:bg-neutral-950"
    style={{ clipPath: "polygon(0 35%, 100% 0, 100% 100%, 0% 100%)" }}
  />
);

/* ---------- right-side graphics ---------- */
const LegendDot = ({ className = "" }: { className?: string }) => (
  <span className={`inline-block h-2.5 w-2.5 rounded-full ${className}`} />
);

const RightClassifierInsight: React.FC = () => {
  const mix = [
    { w: 38, color: "bg-emerald-500", label: "Public" },
    { w: 26, color: "bg-sky-500", label: "Confidential" },
    { w: 22, color: "bg-amber-500", label: "Highly Sensitive" },
    { w: 14, color: "bg-rose-600", label: "Unsafe" },
  ];

  return (
    <motion.div
      variants={staggerParent}
      initial="initial"
      animate="animate"
      className="relative mx-auto w-full max-w-xl lg:max-w-[560px]"
    >
      <motion.div
        variants={staggerItem}
        className="rounded-[28px] border border-white/30 bg-white/80 shadow-2xl ring-1 ring-black/5 backdrop-blur-md dark:border-white/10 dark:bg-neutral-900/70 dark:ring-white/10"
      >
        <div className="flex items-center gap-2 border-b border-black/5 px-6 py-4 dark:border-white/5">
          <span className="inline-flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
          </span>
          <div className="ml-2 text-sm font-semibold text-neutral-700 dark:text-neutral-200">Document Insights</div>
        </div>

        <div className="grid items-stretch gap-6 px-6 py-5 md:grid-cols-2">
          <motion.div variants={staggerItem} className="rounded-2xl border border-black/5 bg-white p-4 text-[13px] leading-relaxed shadow-sm dark:border-white/10 dark:bg-neutral-900">
            <p className="mb-2">
              <span className="rounded px-1.5 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">Our 2025 campus program welcomes applicants worldwide</span> and includes a public overview of benefits. <span className="rounded bg-sky-100 px-1.5 py-0.5 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300">Internal milestone dates are shared with the engineering org</span> for planning only. The form requests <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">SSN and DOB for background checks</span>. Any detected <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300">unsafe content</span> will be automatically escalated to SMEs.
            </p>

            <p>
              <span className="rounded bg-sky-100 px-1.5 py-0.5 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300">Project risk notes and internal process diagrams</span> remain restricted. Marketing copy and images are <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">public-ready</span>.
            </p>
          </motion.div>

          <motion.div variants={staggerItem} className="rounded-2xl bg-white/60 p-4 ring-1 ring-black/5 dark:bg-neutral-900/70 dark:ring-white/10">
            <div className="mb-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400">Category mix</div>
            <div className="mb-2 flex h-4 w-full overflow-hidden rounded-full ring-1 ring-black/5 dark:ring-white/10">
              {mix.map((m, i) => (
                <div key={i} className={`${m.color}`} style={{ width: `${m.w}%` }} />
              ))}
            </div>
            <div className="mb-4 flex flex-wrap gap-4 text-xs">
              <span className="inline-flex items-center gap-1.5"><LegendDot className="bg-emerald-500" /> Public</span>
              <span className="inline-flex items-center gap-1.5"><LegendDot className="bg-sky-500" /> Confidential</span>
              <span className="inline-flex items-center gap-1.5"><LegendDot className="bg-amber-500" /> Highly Sensitive</span>
              <span className="inline-flex items-center gap-1.5"><LegendDot className="bg-rose-600" /> Unsafe</span>
            </div>

            <div className="mb-2 text-sm font-semibold">Top signals</div>
            <div className="space-y-2 text-[13px]">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2"><LegendDot className="bg-amber-500" /> SSN field detected (p2)</div>
                <div className="h-2 w-24 overflow-hidden rounded bg-neutral-200 dark:bg-neutral-800"><div className="h-full w-[78%] bg-amber-500" /></div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2"><LegendDot className="bg-sky-500" /> Internal milestones (p3)</div>
                <div className="h-2 w-24 overflow-hidden rounded bg-neutral-200 dark:bg-neutral-800"><div className="h-full w-[56%] bg-sky-500" /></div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2"><LegendDot className="bg-rose-600" /> Unsafe phrase policy</div>
                <div className="h-2 w-24 overflow-hidden rounded bg-neutral-200 dark:bg-neutral-800"><div className="h-full w-[34%] bg-rose-600" /></div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2"><LegendDot className="bg-emerald-500" /> Public brochure copy (p1)</div>
                <div className="h-2 w-24 overflow-hidden rounded bg-neutral-200 dark:bg-neutral-800"><div className="h-full w-[62%] bg-emerald-500" /></div>
              </div>
            </div>
          </motion.div>
        </div>

        <div className="flex items-center gap-3 border-t border-black/5 px-6 py-4 dark:border-white/5 overflow-x-auto">
          {[
            { label: "Pre-checks", icon: <Search className="h-4 w-4" /> },
            { label: "PII detector", icon: <Lock className="h-4 w-4" /> },
            { label: "Safety monitor", icon: <AlertTriangle className="h-4 w-4" /> },
            { label: "HITL queue", icon: <Users className="h-4 w-4" /> },
          ].map((b) => (
            <button key={b.label} className="inline-flex items-center gap-2 rounded-xl bg-neutral-100 px-3 py-2 text-xs font-medium ring-1 ring-black/5 hover:bg-neutral-200/70 dark:bg-neutral-800/70 dark:ring-white/10 dark:hover:bg-neutral-800 whitespace-nowrap">
              {b.icon}
              {b.label}
            </button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
};

/* ---------- company logos ---------- */
const TrustedBy: React.FC = () => (
  <section className="container mx-auto px-6 pt-32 pb-12">
    <motion.h3
      className="mb-8 text-center text-xl font-semibold text-neutral-800 dark:text-neutral-200"
      {...fade(0)}
    >
    </motion.h3>

    <motion.div
      className="mx-auto grid max-w-5xl grid-cols-3 items-center justify-items-center gap-10 sm:gap-16"
      variants={staggerParent}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, amount: 0.4 }}
    >
      {/* HITACHI */}
      <motion.div
        variants={staggerItem}
        whileHover={{ scale: 1.05 }}
        className="flex flex-col items-center justify-center opacity-80 grayscale transition hover:opacity-100 hover:grayscale-0"
      >
        <img
          src={hitachiLogo}
          alt="Hitachi"
          className="h-8 w-auto mix-blend-multiply dark:mix-blend-lighten"
        />
        <span className="mt-2 text-sm font-medium text-neutral-600 dark:text-neutral-300">
          
        </span>
      </motion.div>

      {/* GOOGLE GEMINI */}
      <motion.div
        variants={staggerItem}
        whileHover={{ scale: 1.05 }}
        className="flex flex-col items-center justify-center opacity-80 grayscale transition hover:opacity-100 hover:grayscale-0"
      >
        <img
          src={geminiLogo}
          alt="Google Gemini"
          className="h-8 w-auto mix-blend-multiply dark:mix-blend-lighten"
        />
        <span className="mt-2 text-sm font-medium text-neutral-600 dark:text-neutral-300">
         
        </span>
      </motion.div>

      {/* DATABRICKS */}
      <motion.div
        variants={staggerItem}
        whileHover={{ scale: 1.05 }}
        className="flex flex-col items-center justify-center opacity-80 grayscale transition hover:opacity-100 hover:grayscale-0"
      >
        <img
          src={databricksLogo}
          alt="Databricks"
          className="h-8 w-auto mix-blend-multiply dark:mix-blend-lighten"
        />
        <span className="mt-2 text-sm font-medium text-neutral-600 dark:text-neutral-300">
          
        </span>
      </motion.div>
    </motion.div>
  </section>
);

/* ---------- why choose us ---------- */
const parentVariants: any = {
  initial: { opacity: 0 },
  whileInView: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants: any = {
  initial: { opacity: 0, y: 14 },
  whileInView: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

const Card = ({ icon, title, body, bg, ring }: { icon: React.ReactNode; title: string; body: string; bg: string; ring: string }) => (
  <motion.div
    variants={itemVariants}
    whileHover={{ y: -6 }}
    className="rounded-2xl border border-neutral-200/70 bg-white/80 p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900/70"
  >
    <div className={`mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl ${bg} ring-1 ${ring}`}>
      {icon}
    </div>
    <h3 className="text-lg font-semibold">{title}</h3>
    <p className="mt-2 text-neutral-600 dark:text-neutral-300">{body}</p>
  </motion.div>
);

const WhyChooseUsSection: React.FC = () => {
  return (
    <section className="container mx-auto px-6 pb-24">
      <motion.h2
        className="mb-3 text-center text-3xl font-bold md:text-4xl"
        initial={{ opacity: 0, y: 8 }}
        whileInView={{ opacity: 1, y: 0, transition: { duration: 0.45 } }}
        viewport={{ once: true, amount: 0.4 }}
      >
        Why choose us
      </motion.h2>

      <motion.p
        className="mx-auto mb-12 max-w-2xl text-center text-neutral-500 dark:text-neutral-400"
        initial={{ opacity: 0, y: 8 }}
        whileInView={{ opacity: 1, y: 0, transition: { duration: 0.45, delay: 0.06 } }}
        viewport={{ once: true, amount: 0.4 }}
      >
        From pre-checks to audit-ready citations, our pipeline is built for accuracy, speed, and reviewer happiness.
      </motion.p>

      <motion.div
        className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
        variants={parentVariants}
        initial="initial"
        whileInView="whileInView"
        viewport={{ once: true, amount: 0.3 }}
      >
        <Card
          icon={<FileText className="h-6 w-6 text-indigo-600" />}
          title="Public content"
          body="Public materials identified with page-level evidence."
          bg="bg-indigo-50 dark:bg-indigo-900/20"
          ring="ring-indigo-200/60 dark:ring-indigo-900/40"
        />

        <Card
          icon={<Shield className="h-6 w-6 text-emerald-600" />}
          title="Confidential clarity"
          body="Internal content labeled for safe sharing and access control."
          bg="bg-emerald-50 dark:bg-emerald-900/20"
          ring="ring-emerald-200/60 dark:ring-emerald-900/40"
        />

        <Card
          icon={<Lock className="h-6 w-6 text-amber-600" />}
          title="Highly sensitive"
          body="PII/SSNs detected with smart redaction suggestions."
          bg="bg-amber-50 dark:bg-amber-900/20"
          ring="ring-amber-200/60 dark:ring-amber-900/40"
        />

        <Card
          icon={<AlertTriangle className="h-6 w-6 text-rose-600" />}
          title="Unsafe monitor"
          body="Harmful content auto-flagged and routed to HITL review."
          bg="bg-rose-50 dark:bg-rose-900/20"
          ring="ring-rose-200/60 dark:ring-rose-900/40"
        />
      </motion.div>
    </section>
  );
};

/* ---------- how it works ---------- */
const Bullet = ({ children }: { children: React.ReactNode }) => (
  <li className="flex items-start gap-3">
    <span className="mt-1 inline-flex h-4 w-4 items-center justify-center">
      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
    </span>
    <span className="text-base text-neutral-700 dark:text-neutral-300">{children}</span>
  </li>
);

const HiwTile = ({
  icon,
  title,
  bullets,
  iconBg,
  ring,
}: {
  icon: React.ReactNode;
  title: string;
  bullets: React.ReactNode[];
  iconBg: string;
  ring: string;
}) => (
  <motion.div
    variants={staggerItem}
    className="rounded-2xl border border-neutral-200/70 bg-white/80 p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md dark:border-neutral-800 dark:bg-neutral-900/70"
  >
    <div className={`mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl ${iconBg} ring-1 ${ring}`}>
      {icon}
    </div>
    <h3 className="mb-4 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>
    <ul className="space-y-3">
      {bullets.map((b, i) => (
        <Bullet key={i}>{b}</Bullet>
      ))}
    </ul>
  </motion.div>
);

const HowItWorksSection: React.FC = () => (
  <section className="container mx-auto px-6 pb-20">
    <motion.div {...fade(0)} className="mx-auto max-w-5xl text-center">
      <h2 className="text-4xl font-extrabold tracking-tight text-neutral-900 dark:text-neutral-100">How it works</h2>
      <p className="mx-auto mt-3 max-w-3xl text-lg text-neutral-600 dark:text-neutral-300">
        A secure, AI-driven pipeline that classifies multi-modal documents with citations, safety checks, and a
        human-in-the-loop review.
      </p>
    </motion.div>

    <motion.div
      className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3"
      variants={staggerParent}
      initial="initial"
      whileInView="animate"
      viewport={{ once: true, amount: 0.4 }}
    >
      <HiwTile
        icon={<FileText className="h-7 w-7 text-indigo-600" />}
        title="Ingest & Pre-checks"
        bullets={[<>Multi-modal input: text, images, video</>, <>Legibility: OCR/contrast checks</>, <>Counts: pages & images per doc</>, <>File safety: type/size validation</>]}
        iconBg="bg-indigo-50 dark:bg-indigo-900/20"
        ring="ring-indigo-200/60 dark:ring-indigo-900/40"
      />
      <HiwTile
        icon={<GitBranch className="h-7 w-7 text-fuchsia-600" />}
        title="Prompt Tree & Analysis"
        bullets={[<>Dynamic prompts from a configurable library</>, <>Classification: Public, Confidential, Highly Sensitive</>, <>Citations: exact pages and image regions</>, <>Modes: Interactive & Batch with live status</>]}
        iconBg="bg-fuchsia-50 dark:bg-fuchsia-900/20"
        ring="ring-fuchsia-200/60 dark:ring-fuchsia-900/40"
      />
      <HiwTile
        icon={<Shield className="h-7 w-7 text-emerald-600" />}
        title="Safety & HITL"
        bullets={[<>Safety monitor auto-detects unsafe content</>, <>HITL queue for SME validation & feedback</>, <>Redaction tips for PII & sensitive regions</>, <>Audit trail of reviewer actions</>]}
        iconBg="bg-emerald-50 dark:bg-emerald-900/20"
        ring="ring-emerald-200/60 dark:ring-emerald-900/40"
      />
    </motion.div>
  </section>
);

/* ---------- page ---------- */
const Home: React.FC = () => {
  return (
    <div className="relative min-h-screen overflow-clip text-neutral-900 dark:text-neutral-100">
      {/* Stripe-style hero */}
      <HeroGradientBg />
      <SlantedDivider />

      {/* HERO — content sits on top of gradient */}
      <section className="container mx-auto grid items-center gap-10 px-6 pt-20 pb-16 lg:grid-cols-2">
        {/* left copy */}
        <div>
          <motion.div
            {...fade(0)}
            className="inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/40 backdrop-blur"
          >
            <Shield className="h-4 w-4" />
            AI-powered document security
          </motion.div>

          <motion.h1 {...fade(0.08)} className="mt-6 text-5xl font-extrabold leading-tight tracking-tight text-white md:text-6xl">
            Document infrastructure
            <br />
            to secure your data
          </motion.h1>

          <motion.p {...fade(0.16)} className="mt-5 max-w-xl text-lg text-white/90">
            Classify multi-modal documents, surface citations, and enforce safety policies with a human-in-the-loop
            workflow.
          </motion.p>

          <motion.div {...fade(0.24)} className="mt-7 flex flex-wrap gap-4">
            <Link to="/upload">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                className="rounded-full bg-neutral-900/90 px-7 py-3 font-semibold text-white shadow-lg shadow-black/20 backdrop-blur transition hover:bg-neutral-900"
              >
                Get started
              </motion.button>
            </Link>
            <Link to="/dashboard">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                className="rounded-full bg-white/25 px-7 py-3 font-semibold text-white ring-1 ring-white/50 backdrop-blur hover:bg-white/35"
              >
                View dashboard
              </motion.button>
            </Link>
          </motion.div>
        </div>

        {/* RIGHT: document classification insight */}
        <div className="relative">
          <RightClassifierInsight />
        </div>
      </section>

      {/* Logos (optional) */}
      <TrustedBy />

      {/* Why choose us */}
      <WhyChooseUsSection />

      {/* How it works */}
      <HowItWorksSection />

    </div>
  );
};

export default Home;