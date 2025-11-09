import { useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload as UploadIcon, FileText, CheckCircle, AlertTriangle, Lock, Eye, X, Loader2, Clock, CheckCircle2, ArrowRight } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { motion } from "framer-motion";
import { uploadDocument, classifyDocument } from "@/services/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useQueryClient } from "@tanstack/react-query";
import { DASHBOARD_QUERY_KEY } from "@/hooks/use-dashboard-data";

const float = (delay = 0): any => ({
  initial: { opacity: 0, y: 12, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1, transition: { delay, duration: 0.5, ease: "easeOut" } },
});

interface Citation {
  page: number;
  snippet: string;
  image_index?: number | null;
  region?: string | null;
  source?: string;
}

interface AnalysisResult {
  fileName: string;
  classification: string;
  secondaryTags: string[];
  pages: number;
  images: number;
  confidence: number;
  explanation: string;
  citations: Citation[];
  safetyCheck: {
    isSafe: boolean;
    contentSafety: string;
    concerns: string[];
  };
  legibilityScore: number;
  dualLlmAgreement: number;
  requiresReview: boolean;
  primaryAnalysis: {
    model: string;
    confidence: number;
    explanation: string;
  };
  secondaryAnalysis: {
    model: string;
    confidence: number;
    explanation: string;
  };
}

interface BatchJob {
  job_id: string;
  total_files: number;
  completed: number;
  failed: number;
  progress: number;
  status: string;
  documents: Array<{
    doc_id: string;
    filename: string;
    status: string;
    progress: number;
    error?: string;
  }>;
}

const Upload = () => {
  const [mode, setMode] = useState<"interactive" | "batch">("interactive");
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  
  // Batch mode state
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [batchJob, setBatchJob] = useState<BatchJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const analyzeDocument = async (file: File) => {
    setIsProcessing(true);
    setProgress(0);
    setStatusMessage("Uploading document...");

    try {
      // Step 1: Upload document (0-40%)
      setProgress(10);
      setStatusMessage(`Uploading ${file.name}...`);
      const uploadData = await uploadDocument(file);
      const docId = uploadData.doc_id;
      setProgress(40);
      setStatusMessage("Upload complete. Extracting text and images...");

      // Small delay to show the status
      await new Promise(resolve => setTimeout(resolve, 500));

      // Step 2: Classify document (40-100%)
      setProgress(50);
      setStatusMessage("Running AI classification...");
      
      // Simulate progressive updates during classification
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev < 90) return prev + 2;
          return prev;
        });
      }, 200);

      const classifyData = await classifyDocument(docId);
      
      clearInterval(progressInterval);
      setProgress(95);
      setStatusMessage("Analyzing dual LLM consensus...");
      
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setProgress(100);
      setStatusMessage("Analysis complete!");

      // Map backend response to frontend format
      const analysisResult: AnalysisResult = {
        fileName: file.name,
        classification: classifyData.final_category || "Unknown",
        secondaryTags: classifyData.secondary_tags || [],
        pages: classifyData.page_count || 0,
        images: classifyData.image_count || 0,
        confidence: Math.round((classifyData.confidence || 0) * 100),
        explanation: classifyData.explanation || "Classification based on AI analysis of document content.",
        citations: classifyData.citations || [],
        safetyCheck: {
          isSafe: !classifyData.raw_signals.has_pii && !classifyData.raw_signals.has_unsafe_pattern,
          contentSafety: classifyData.content_safety || "Content safety not assessed",
          concerns: [
            ...(classifyData.raw_signals.has_pii ? ["PII detected in document"] : []),
            ...(classifyData.raw_signals.has_unsafe_pattern ? ["Unsafe content detected"] : []),
            ...classifyData.raw_signals.pii_hits,
            ...classifyData.raw_signals.unsafe_hits,
          ],
        },
        legibilityScore: classifyData.legibility_score || 0,
        dualLlmAgreement: classifyData.dual_llm_agreement || 0,
        requiresReview: classifyData.requires_review || false,
        primaryAnalysis: {
          model: classifyData.primary_analysis.model,
          confidence: Math.round((classifyData.primary_analysis.confidence || 0) * 100),
          explanation: classifyData.primary_analysis.explanation,
        },
        secondaryAnalysis: {
          model: classifyData.secondary_analysis.model,
          confidence: Math.round((classifyData.secondary_analysis.confidence || 0) * 100),
          explanation: classifyData.secondary_analysis.explanation,
        },
      };

      setResult(analysisResult);
      
      // Invalidate dashboard cache to refresh with new document
      queryClient.invalidateQueries({ queryKey: [DASHBOARD_QUERY_KEY] });
      
      toast({
        title: "Analysis Complete",
        description: `Document classified as ${analysisResult.classification}`,
      });
    } catch (error) {
      console.error("Analysis error:", error);
      setStatusMessage("Analysis failed");
      toast({
        title: "Analysis Failed",
        description: error instanceof Error ? error.message : "Failed to analyze document",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Batch processing functions
  const handleBatchUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    setIsProcessing(true);
    setStatusMessage(`Uploading ${files.length} files...`);
    setBatchFiles(files);
    
    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      setStatusMessage("Sending files to server...");
      const response = await fetch(`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/batch/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Batch upload failed");
      }

      const data = await response.json();
      setStatusMessage("Batch processing started. Monitoring progress...");
      
      setBatchJob({
        job_id: data.job_id,
        total_files: data.total_files,
        completed: 0,
        failed: 0,
        progress: 0,
        status: data.status,
        documents: [],
      });

      // Start polling for job status
      setIsPolling(true);
      pollJobStatus(data.job_id);

      toast({
        title: "Batch Upload Started",
        description: `Processing ${data.total_files} documents`,
      });
    } catch (error) {
      console.error("Batch upload error:", error);
      setStatusMessage("Batch upload failed");
      toast({
        title: "Batch Upload Failed",
        description: error instanceof Error ? error.message : "Failed to start batch processing",
        variant: "destructive",
      });
      setIsProcessing(false);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/status/${jobId}`);
        
        if (!response.ok) {
          throw new Error("Failed to fetch job status");
        }

        const data = await response.json();
        
        // Update status message based on progress
        const processingCount = data.total_files - data.completed - data.failed;
        if (processingCount > 0) {
          setStatusMessage(`Processing ${processingCount} documents... (${data.completed} completed, ${data.failed} failed)`);
        } else if (data.status === "completed") {
          setStatusMessage("All documents processed successfully!");
        } else if (data.status === "failed") {
          setStatusMessage("Batch processing encountered errors");
        }
        
        setBatchJob({
          job_id: data.job_id,
          total_files: data.total_files,
          completed: data.completed,
          failed: data.failed,
          progress: data.progress,
          status: data.status,
          documents: data.documents,
        });

        // Stop polling if job is complete or failed
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(pollInterval);
          setIsPolling(false);
          setIsProcessing(false);
          setStatusMessage(data.status === "completed" 
            ? `Batch complete! ${data.completed} documents processed.` 
            : `Batch failed. ${data.completed} completed, ${data.failed} failed.`);
          
          // Invalidate dashboard cache to refresh with new documents
          queryClient.invalidateQueries({ queryKey: [DASHBOARD_QUERY_KEY] });
          
          toast({
            title: data.status === "completed" ? "Batch Processing Complete" : "Batch Processing Failed",
            description: `Processed: ${data.completed}, Failed: ${data.failed}`,
            variant: data.status === "completed" ? "default" : "destructive",
          });
        }
      } catch (error) {
        console.error("Polling error:", error);
        clearInterval(pollInterval);
        setIsPolling(false);
        setIsProcessing(false);
        setStatusMessage("Failed to fetch job status");
      }
    }, 2000); // Poll every 2 seconds
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (mode === "batch") {
      handleBatchUpload(files);
    } else if (files.length > 0) {
      analyzeDocument(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    if (mode === "batch") {
      handleBatchUpload(Array.from(files));
    } else {
      analyzeDocument(files[0]);
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

          {/* Mode Selector */}
          <motion.div {...float(0.05)} className="mb-6">
            <Tabs value={mode} onValueChange={(v) => setMode(v as "interactive" | "batch")} className="w-full">
              <TabsList className="grid w-full max-w-md mx-auto grid-cols-2 rounded-2xl bg-white/80 p-1 backdrop-blur-md dark:bg-neutral-900/70">
                <TabsTrigger value="interactive" className="rounded-xl data-[state=active]:bg-gradient-to-br data-[state=active]:from-emerald-500 data-[state=active]:to-purple-600 data-[state=active]:text-white">
                  Interactive Mode
                </TabsTrigger>
                <TabsTrigger value="batch" className="rounded-xl data-[state=active]:bg-gradient-to-br data-[state=active]:from-purple-500 data-[state=active]:to-fuchsia-600 data-[state=active]:text-white">
                  Batch Processing
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </motion.div>

          {/* Upload Area */}
          {!result && !batchJob && (
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
                      {isDragging ? "Drop your files here" : mode === "batch" ? "Upload Multiple Documents" : "Upload Document"}
                    </h3>
                    <p className="text-neutral-600 dark:text-neutral-400">
                      {mode === "batch" ? "Drag and drop multiple files or click to browse" : "Drag and drop a file or click to browse"}
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
                      multiple={mode === "batch"}
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
                    <Loader2 className="relative w-8 h-8 text-purple-600 dark:text-purple-400 animate-spin" />
                  </motion.div>
                  <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {mode === "batch" ? "Processing Batch..." : "Analyzing Document..."}
                  </h3>
                  <motion.p 
                    className="text-neutral-600 dark:text-neutral-400 min-h-[24px]"
                    key={statusMessage}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {statusMessage || "Processing multi-modal content and generating classification"}
                  </motion.p>
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
                      <div className="flex-1">
                        <h2 className="text-2xl font-bold mb-1 text-neutral-900 dark:text-neutral-100">{result.fileName}</h2>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {result.secondaryTags.map((tag, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
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

                  {/* Main Stats Grid */}
                  <div className="grid md:grid-cols-4 gap-4 mb-6">
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
                    <div className="space-y-1">
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Legibility</div>
                      <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                        {Math.round(result.legibilityScore * 100)}%
                      </div>
                    </div>
                  </div>

                  {/* Explanation */}
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">Analysis Explanation</h3>
                      <p className="text-neutral-600 dark:text-neutral-400">{result.explanation}</p>
                    </div>

                    {/* Citations & Evidence */}
                    <div>
                      <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">
                        Citations & Evidence ({result.citations.length})
                      </h3>
                      <div className="max-h-96 overflow-y-auto space-y-3">
                        {result.citations.map((citation, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-sm p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
                            <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
                            <div className="flex-1 space-y-1">
                              <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                                <span>Page {citation.page}</span>
                                {citation.image_index && <span>• Image {citation.image_index}</span>}
                                {citation.source && <Badge variant="outline" className="text-xs">{citation.source}</Badge>}
                              </div>
                              <p className="text-neutral-600 dark:text-neutral-300">{citation.snippet}</p>
                              {citation.region && (
                                <p className="text-xs text-neutral-500 dark:text-neutral-400">Region: {citation.region}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Safety Check */}
                    <div>
                      <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">Content Safety</h3>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          {result.safetyCheck.isSafe ? (
                            <>
                              <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                {result.safetyCheck.contentSafety}
                              </span>
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
                              <span className="text-rose-600 dark:text-rose-400 font-medium">Safety concerns detected</span>
                            </>
                          )}
                        </div>
                        {result.safetyCheck.concerns.length > 0 && (
                          <ul className="ml-7 space-y-1">
                            {result.safetyCheck.concerns.map((concern, idx) => (
                              <li key={idx} className="text-sm text-neutral-600 dark:text-neutral-400">• {concern}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>

                    {/* Dual LLM Analysis */}
                    <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
                      <h3 className="font-semibold mb-3 text-neutral-900 dark:text-neutral-100">Dual LLM Validation</h3>
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="text-sm text-neutral-600 dark:text-neutral-400">Agreement Score:</div>
                          <div className="text-lg font-bold text-neutral-900 dark:text-neutral-100">
                            {Math.round(result.dualLlmAgreement * 100)}%
                          </div>
                          {result.requiresReview && (
                            <Badge variant="warning" className="ml-2">Requires Review</Badge>
                          )}
                        </div>
                        
                        <div className="grid md:grid-cols-2 gap-4">
                          {/* Primary Analysis */}
                          <div className="p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 space-y-2">
                            <div className="flex items-center justify-between">
                              <h4 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100">Primary Analysis</h4>
                              <Badge variant="outline" className="text-xs">{result.primaryAnalysis.model}</Badge>
                            </div>
                            <div className="text-sm text-neutral-600 dark:text-neutral-400">
                              Confidence: <span className="font-semibold">{result.primaryAnalysis.confidence}%</span>
                            </div>
                            <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-3">
                              {result.primaryAnalysis.explanation}
                            </p>
                          </div>

                          {/* Secondary Analysis */}
                          <div className="p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 space-y-2">
                            <div className="flex items-center justify-between">
                              <h4 className="font-semibold text-sm text-neutral-900 dark:text-neutral-100">Secondary Analysis</h4>
                              <Badge variant="outline" className="text-xs">{result.secondaryAnalysis.model}</Badge>
                            </div>
                            <div className="text-sm text-neutral-600 dark:text-neutral-400">
                              Confidence: <span className="font-semibold">{result.secondaryAnalysis.confidence}%</span>
                            </div>
                            <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-3">
                              {result.secondaryAnalysis.explanation}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>

              {/* Completion message */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25, duration: 0.4 }}
              >
                <Card className="p-6 rounded-2xl border-emerald-500/30 bg-emerald-50/80 dark:border-emerald-500/30 dark:bg-emerald-900/20 backdrop-blur-md">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <CheckCircle className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-emerald-900 dark:text-emerald-100 mb-1">
                        Document Classified Successfully!
                      </h4>
                      <p className="text-sm text-emerald-700 dark:text-emerald-300">
                        Classification complete. This document is automatically saved and available in the dashboard.
                      </p>
                    </div>
                  </div>
                </Card>
              </motion.div>

              <motion.div 
                className="flex justify-center gap-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                <Link to="/dashboard">
                  <Button 
                    size="lg" 
                    className="rounded-full bg-gradient-to-r from-emerald-600 to-emerald-700 px-8 py-3 font-semibold text-white shadow-lg hover:from-emerald-700 hover:to-emerald-800 gap-2"
                  >
                    View Dashboard
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
                <Button 
                  size="lg" 
                  onClick={() => setResult(null)}
                  variant="outline"
                  className="rounded-full px-8 py-3 font-semibold shadow-lg"
                >
                  Analyze Another Document
                </Button>
              </motion.div>
            </div>
          )}

          {/* Batch Processing Results */}
          {batchJob && (
            <motion.div {...float(0.2)} className="space-y-6">
              <Card className="p-8 rounded-2xl border-white/30 bg-white/80 shadow-xl backdrop-blur-md dark:border-neutral-800 dark:bg-neutral-900/70">
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                        Batch Processing
                      </h3>
                      {statusMessage && (
                        <motion.p 
                          className="text-sm text-neutral-600 dark:text-neutral-400 mt-1"
                          key={statusMessage}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          {statusMessage}
                        </motion.p>
                      )}
                    </div>
                    <Badge 
                      variant={batchJob.status === "completed" ? "default" : batchJob.status === "failed" ? "destructive" : "secondary"}
                      className="text-sm px-3 py-1"
                    >
                      {batchJob.status === "processing" ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Processing
                        </div>
                      ) : batchJob.status === "completed" ? (
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4" />
                          Completed
                        </div>
                      ) : (
                        batchJob.status
                      )}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="text-center p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
                      <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{batchJob.total_files}</div>
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Total Files</div>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                      <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{batchJob.completed}</div>
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Completed</div>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-rose-50 dark:bg-rose-900/20">
                      <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">{batchJob.failed}</div>
                      <div className="text-sm text-neutral-600 dark:text-neutral-400">Failed</div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between text-sm text-neutral-600 dark:text-neutral-400">
                      <span>Overall Progress</span>
                      <span>{Math.round(batchJob.progress)}%</span>
                    </div>
                    <Progress value={batchJob.progress} className="h-2" />
                  </div>
                </div>

                {/* Document List */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
                    Documents {isPolling && <span className="text-sm font-normal text-neutral-500">(updating live...)</span>}
                  </h4>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {batchJob.documents.map((doc) => (
                      <motion.div 
                        key={doc.doc_id}
                        layout
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                        className="p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <motion.div 
                            className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
                              doc.status === "completed" ? "bg-emerald-100 dark:bg-emerald-900/30" :
                              doc.status === "failed" ? "bg-rose-100 dark:bg-rose-900/30" :
                              doc.status === "processing" ? "bg-purple-100 dark:bg-purple-900/30" :
                              "bg-neutral-200 dark:bg-neutral-700"
                            }`}
                            animate={doc.status === "processing" ? { scale: [1, 1.1, 1] } : {}}
                            transition={{ repeat: doc.status === "processing" ? Infinity : 0, duration: 1.5 }}
                          >
                            {doc.status === "completed" ? (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 200 }}
                              >
                                <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                              </motion.div>
                            ) : doc.status === "failed" ? (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 200 }}
                              >
                                <AlertTriangle className="h-5 w-5 text-rose-600 dark:text-rose-400" />
                              </motion.div>
                            ) : doc.status === "processing" ? (
                              <Loader2 className="h-5 w-5 text-purple-600 dark:text-purple-400 animate-spin" />
                            ) : (
                              <Clock className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
                            )}
                          </motion.div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm text-neutral-900 dark:text-neutral-100 truncate">
                              {doc.filename}
                            </p>
                            {doc.error ? (
                              <motion.p 
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-xs text-rose-600 dark:text-rose-400 truncate"
                              >
                                {doc.error}
                              </motion.p>
                            ) : doc.status === "processing" ? (
                              <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-xs text-purple-600 dark:text-purple-400"
                              >
                                Processing...
                              </motion.p>
                            ) : doc.status === "completed" ? (
                              <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-xs text-emerald-600 dark:text-emerald-400"
                              >
                                Complete
                              </motion.p>
                            ) : null}
                          </div>
                        </div>
                        <div className="flex-shrink-0 ml-4">
                          <Progress value={doc.progress} className="h-1 w-24" />
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </Card>

              {/* Completion message and actions */}
              {(batchJob.status === "completed" || batchJob.status === "failed") && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.4 }}
                >
                  <Card className="p-6 rounded-2xl border-emerald-500/30 bg-emerald-50/80 dark:border-emerald-500/30 dark:bg-emerald-900/20 backdrop-blur-md">
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <CheckCircle className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-emerald-900 dark:text-emerald-100 mb-1">
                          Batch Processing Complete!
                        </h4>
                        <p className="text-sm text-emerald-700 dark:text-emerald-300">
                          All documents have been processed and classified. Results are automatically saved and available in the dashboard.
                        </p>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )}

              <motion.div 
                className="flex justify-center gap-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                {(batchJob.status === "completed" || batchJob.status === "failed") && (
                  <Link to="/dashboard">
                    <Button 
                      size="lg" 
                      className="rounded-full bg-gradient-to-r from-emerald-600 to-emerald-700 px-8 py-3 font-semibold text-white shadow-lg hover:from-emerald-700 hover:to-emerald-800 gap-2"
                    >
                      View Dashboard
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  </Link>
                )}
                <Button 
                  size="lg" 
                  onClick={() => {
                    setBatchJob(null);
                    setBatchFiles([]);
                  }}
                  variant={(batchJob.status === "completed" || batchJob.status === "failed") ? "outline" : "default"}
                  className="rounded-full px-8 py-3 font-semibold shadow-lg"
                >
                  Process New Batch
                </Button>
              </motion.div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Upload;

