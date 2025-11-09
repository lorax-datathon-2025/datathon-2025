import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload as UploadIcon, FileText, CheckCircle, AlertTriangle, Lock, Eye, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { motion } from "framer-motion";

const float = (delay = 0): any => ({
  initial: { opacity: 0, y: 12, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1, transition: { delay, duration: 0.5, ease: "easeOut" } },
});

interface AnalysisResult {
  fileName: string;
  classification: string;
  pages: number;
  images: number;
  confidence: number;
  summary: string;
  reasoning: string;
  citations: string[];
  safetyCheck: {
    isSafe: boolean;
    concerns: string[];
  };
}

const Upload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const { toast } = useToast();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const simulateAnalysis = async (fileName: string) => {
    setIsProcessing(true);
    setProgress(0);

    // Simulate progress
    const intervals = [10, 25, 45, 65, 85, 100];
    for (const target of intervals) {
      await new Promise(resolve => setTimeout(resolve, 500));
      setProgress(target);
    }

    // Mock analysis result
    const classifications = ["Public", "Confidential", "Highly Sensitive", "Unsafe"];
    const randomClassification = classifications[Math.floor(Math.random() * classifications.length)];
    
    const mockResult: AnalysisResult = {
      fileName,
      classification: randomClassification,
      pages: Math.floor(Math.random() * 20) + 1,
      images: Math.floor(Math.random() * 10),
      confidence: Math.floor(Math.random() * 20) + 80,
      summary: "Document analyzed successfully with multi-modal content processing.",
      reasoning: `This document has been classified as ${randomClassification} based on the presence of specific content markers, terminology, and data patterns identified through AI analysis.`,
      citations: [
        `Page 1: Classification marker detected`,
        `Page 3: Relevant content identified`,
        `Image 2: Visual analysis completed`,
      ],
      safetyCheck: {
        isSafe: randomClassification !== "Unsafe",
        concerns: randomClassification === "Unsafe" 
          ? ["Potentially harmful content detected", "Requires human review"]
          : [],
      },
    };

    setResult(mockResult);
    setIsProcessing(false);
    
    toast({
      title: "Analysis Complete",
      description: `Document classified as ${randomClassification}`,
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      simulateAnalysis(files[0].name);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      simulateAnalysis(files[0].name);
    }
  };

  const getClassificationColor = (classification: string) => {
    switch (classification) {
      case "Public": return "success";
      case "Confidential": return "info";
      case "Highly Sensitive": return "warning";
      case "Unsafe": return "destructive";
      default: return "secondary";
    }
  };

  const getClassificationIcon = (classification: string) => {
    switch (classification) {
      case "Public": return <CheckCircle className="w-5 h-5" />;
      case "Confidential": return <Eye className="w-5 h-5" />;
      case "Highly Sensitive": return <Lock className="w-5 h-5" />;
      case "Unsafe": return <AlertTriangle className="w-5 h-5" />;
      default: return <FileText className="w-5 h-5" />;
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* bottom slanted gradient background) */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-[260px] overflow-hidden"
        style={{ clipPath: "polygon(0 40%, 100% 0, 100% 100%, 0 100%)" }}
      >
        <div
          className="absolute inset-0 opacity-70"
          style={{
            background:
              "radial-gradient(800px 400px at 95% 110%, rgba(52,211,153,.6), transparent 45%), radial-gradient(700px 480px at 5% 80%, rgba(139,92,246,.5), transparent 45%), radial-gradient(600px 360px at 60% 90%, rgba(236,72,153,.5), transparent 45%), linear-gradient(240deg, #10b981 0%, #8b5cf6 40%, #ec4899 80%)",
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

      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute top-[10%] left-[8%] h-[220px] w-[220px] rounded-full bg-purple-500/20 blur-3xl" />
        <div className="absolute bottom-[26%] right-[8%] h-[200px] w-[200px] rounded-full bg-emerald-500/20 blur-3xl" />
        <div className="absolute bottom-[6%] left-[22%] h-[180px] w-[180px] rounded-full bg-fuchsia-500/20 blur-3xl" />
      </div>

      <div className="container relative z-10 mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h1 className="text-4xl font-extrabold tracking-tight text-neutral-900 dark:text-neutral-100 mb-2">Upload & Analyze</h1>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Upload documents for AI-powered classification and security analysis
            </p>
          </motion.div>

          {/* Upload Area */}
          {!result && (
            <motion.div {...float(0.1)}>
              <Card 
                className={`p-12 border-2 border-dashed transition-all rounded-2xl shadow-xl backdrop-blur-md ${
                  isDragging 
                    ? "border-emerald-500 bg-emerald-500/10 dark:border-emerald-400" 
                    : "border-white/30 bg-white/80 hover:border-purple-400/50 dark:border-neutral-700 dark:bg-neutral-900/70"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <div className="text-center space-y-6">
                  <motion.div 
                    className="relative w-20 h-20 rounded-full flex items-center justify-center mx-auto overflow-hidden"
                    whileHover={{ scale: 1.05 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500 via-purple-500 to-fuchsia-500 opacity-90" />
                    <UploadIcon className="relative w-10 h-10 text-white" />
                  </motion.div>
                  
                  <div>
                    <h3 className="text-xl font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
                      {isDragging ? "Drop your files here" : "Upload Documents"}
                    </h3>
                    <p className="text-neutral-600 dark:text-neutral-400">
                      Drag and drop files or click to browse
                    </p>
                    <p className="text-sm text-neutral-500 dark:text-neutral-500 mt-2">
                      Supports PDF, DOCX, images, and multi-modal documents
                    </p>
                  </div>

                  <div>
                    <input
                      type="file"
                      id="file-upload"
                      className="hidden"
                      onChange={handleFileInput}
                      accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
                    />
                    <label htmlFor="file-upload">
                      <Button size="lg" asChild className="rounded-full bg-neutral-900 px-6 py-3 font-semibold text-white shadow-lg hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100">
                        <span className="cursor-pointer">Select Files</span>
                      </Button>
                    </label>
                  </div>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Processing State */}
          {isProcessing && (
            <motion.div {...float(0.15)}>
              <Card className="p-8 space-y-6 rounded-2xl border-white/30 bg-white/80 shadow-xl backdrop-blur-md dark:border-neutral-800 dark:bg-neutral-900/70">
                <div className="text-center space-y-4">
                  <motion.div 
                    className="relative w-16 h-16 rounded-full flex items-center justify-center mx-auto overflow-hidden"
                    animate={{ 
                      scale: [1, 1.05, 1],
                      rotate: [0, 5, -5, 0]
                    }}
                    transition={{ 
                      repeat: Infinity, 
                      duration: 2,
                      ease: "easeInOut"
                    }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500 via-purple-500 to-fuchsia-500 opacity-20" />
                    <FileText className="relative w-8 h-8 text-purple-600 dark:text-purple-400" />
                  </motion.div>
                  <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">Analyzing Document...</h3>
                  <p className="text-neutral-600 dark:text-neutral-400">
                    Processing multi-modal content and generating classification
                  </p>
                </div>
                
                <div className="space-y-2">
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
                    <motion.div
                      className="h-full bg-gradient-to-r from-emerald-500 via-purple-500 to-fuchsia-500"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-sm text-center text-neutral-600 dark:text-neutral-400">{progress}% complete</p>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Results */}
          {result && !isProcessing && (
            <div className="space-y-6">
              <motion.div {...float(0.2)}>
                <Card className="p-8 rounded-2xl border-white/30 bg-white/80 shadow-xl backdrop-blur-md dark:border-neutral-800 dark:bg-neutral-900/70">
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex items-start gap-4">
                      <div className="relative w-16 h-16 rounded-xl flex items-center justify-center overflow-hidden">
                        <div className={`absolute inset-0 ${
                          result.classification === "Public" ? "bg-emerald-500/15" :
                          result.classification === "Confidential" ? "bg-sky-500/15" :
                          result.classification === "Highly Sensitive" ? "bg-amber-500/15" :
                          "bg-rose-500/15"
                        }`} />
                        <div className="relative">
                          {getClassificationIcon(result.classification)}
                        </div>
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold mb-1 text-neutral-900 dark:text-neutral-100">{result.fileName}</h2>
                        <p className="text-neutral-600 dark:text-neutral-400">{result.summary}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setResult(null)}
                      className="hover:bg-neutral-100 dark:hover:bg-neutral-800"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>

                  <div className="grid md:grid-cols-3 gap-4 mb-6">
                    <div className="space-y-1">
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Classification</div>
                      <Badge 
                        variant={getClassificationColor(result.classification) as any}
                        className="text-base"
                      >
                        {result.classification}
                      </Badge>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Confidence</div>
                      <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{result.confidence}%</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Content</div>
                      <div className="text-base text-neutral-900 dark:text-neutral-100">
                        {result.pages} pages, {result.images} images
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">Reasoning</h3>
                      <p className="text-neutral-600 dark:text-neutral-400">{result.reasoning}</p>
                    </div>

                    <div>
                      <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">Citations & Evidence</h3>
                      <ul className="space-y-2">
                        {result.citations.map((citation, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
                            <span className="text-neutral-600 dark:text-neutral-400">{citation}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">Safety Check</h3>
                      {result.safetyCheck.isSafe ? (
                        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle className="w-5 h-5" />
                          <span>Content is safe for distribution</span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
                            <AlertTriangle className="w-5 h-5" />
                            <span>Safety concerns detected</span>
                          </div>
                          <ul className="ml-7 space-y-1">
                            {result.safetyCheck.concerns.map((concern, idx) => (
                              <li key={idx} className="text-sm text-neutral-600 dark:text-neutral-400">• {concern}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>

              <motion.div 
                className="flex justify-center"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                <Button 
                  size="lg" 
                  onClick={() => setResult(null)}
                  className="rounded-full bg-neutral-900 px-8 py-3 font-semibold text-white shadow-lg hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100"
                >
                  Analyze Another Document
                </Button>
              </motion.div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Upload;

