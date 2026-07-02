import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, Zap } from "lucide-react";

export default function Hero() {
  return (
    <section id="hero" className="relative min-h-screen w-full overflow-hidden flex flex-col justify-center">
      <div className="absolute inset-0 bg-[url('/assets/hero/Hero-BG.svg')] bg-cover bg-center" />
      <div className="absolute inset-0 bg-black/25" />

      <div className="relative z-10 text-center px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full pt-30">



        <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-medium mb-6 leading-[1.1] tracking-tight" style={{ fontFamily: 'Poppins, sans-serif' }}>
          <span className="text-white">Build </span>
          <span className="text-[#1D4ED8]">Intelligent Workflows</span>
          <br />
          <span className="text-white">In Minutes.</span>
        </h1>

        <p className="text-base sm:text-lg lg:text-xl text-white/80 mb-10 max-w-3xl mx-auto leading-relaxed font-normal" style={{ fontFamily: 'Poppins, sans-serif' }}>
          The ultimate visual workflow builder powered by multiple LLMs (OpenAI, Claude, Gemini, Groq). Automate your business logic effortlessly.
        </p>

        <div className="flex flex-col sm:flex-row gap-6 justify-center items-center mb-20">
          <Link href="/sign-in" className="bg-[#1D4ED8] hover:bg-[#1E40AF] text-white font-bold px-10 py-4 rounded-xl neon-glow hover-lift transition-all duration-300 flex items-center gap-3 text-lg">
            Get Started
            <ArrowRight className="w-5 h-5" />
          </Link>

          <a href="#features" className="glass border-2 border-white/20 hover:border-[#1D4ED8]/50 text-white font-bold px-10 py-4 rounded-xl hover-lift transition-all duration-300 flex items-center gap-3 text-lg">
            <Zap className="w-5 h-5" />
            Learn More
          </a>
        </div>

        <div className="w-full max-w-4xl mx-auto mt-12">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-[#1D4ED8] text-sm font-medium mb-2" style={{ fontFamily: 'Poppins, sans-serif' }}>Clients</div>
              <div className="text-4xl font-semibold text-white" style={{ fontFamily: 'Poppins, sans-serif' }}>120+</div>
            </div>
            <div className="text-center">
              <div className="text-[#1D4ED8] text-sm font-medium mb-2" style={{ fontFamily: 'Poppins, sans-serif' }}>Projects</div>
              <div className="text-4xl font-semibold text-white" style={{ fontFamily: 'Poppins, sans-serif' }}>15+</div>
            </div>
            <div className="text-center">
              <div className="text-[#1D4ED8] text-sm font-medium mb-2" style={{ fontFamily: 'Poppins, sans-serif' }}>5-Star Reviews</div>
              <div className="text-4xl font-semibold text-white" style={{ fontFamily: 'Poppins, sans-serif' }}>32+</div>
            </div>
          </div>
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
    </section>
  );
}
