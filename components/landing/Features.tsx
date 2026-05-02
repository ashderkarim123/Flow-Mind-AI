"use client";

import { motion } from "framer-motion";
import Image from "next/image";

const features = [
  {
    title: "Visual Workflow Builder",
    desc: "Design complex logic effortlessly using our intuitive drag-and-drop interactive canvas."
  },
  {
    title: "Multi-Model AI Selection", 
    desc: "Choose between GPT-4, Claude 3, Gemini, or Groq to power each node in your workflow."
  },
  {
    title: "Secure User Module",
    desc: "Manage your credentials securely, monitor analytics, and organize execution logs from one dashboard."
  },
  {
    title: "Dynamic Execution",
    desc: "Test, compare, and deploy intelligent agents that run seamlessly in our optimized Python backend."
  }
];

const FeatureCard = ({ feature, index }: { feature: typeof features[0], index: number }) => {
  // Asymmetric widths per row: left (narrow) / right (wide), repeated for row 2
  const cardSpans = [
    "md:col-span-5", // left - row 1 (narrow)
    "md:col-span-7", // right - row 1 (wide)
    "md:col-span-7", // left - row 2 (wide)
    "md:col-span-5", // right - row 2 (narrow)
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      viewport={{ once: true }}
      className={`group cursor-pointer col-span-12 ${cardSpans[index]}`}
    >
      <div className="relative min-h-[220px] lg:min-h-[260px] p-6 lg:p-8 rounded-3xl border border-[#1D4ED8]/60 hover:border-[#1D4ED8] transition-all duration-300 h-full text-white" style={{ background: 'linear-gradient(135deg, rgba(0,0,0,0.3) 0%, rgba(39,40,41,0.7) 70%, rgba(255,105,0,0.3) 100%)' }}>
        {/* Orange arrow icon */}
        <div className="absolute top-6 right-6 w-12 h-12 bg-[#1D4ED8] rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
          <Image
            src="/assets/feature/Arrow.svg"
            alt="Arrow"
            width={16}
            height={16}
            className="w-8 h-8"
          />
        </div>
        
        {/* Content: description on top, heading at bottom */}
        <div className="mt-6 lg:mt-2 h-full flex flex-col justify-between pb-4 lg:pb-6 pr-15">
          <p className="text-white/85 leading-relaxed" style={{ fontFamily: 'Poppins, sans-serif' }}>
            {feature.desc}
          </p>
          <h3 className="text-2xl font-medium text-white mt-4 lg:mt-5 pt-1" style={{ fontFamily: 'Poppins, sans-serif' }}>
            {feature.title}
          </h3>
        </div>
      </div>
    </motion.div>
  );
};

const Features = () => {
  return (
    <section id="features" className="relative py-20 bg-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="mb-12 max-w-6xl mx-auto"
        >
          <div className="flex items-start justify-between gap-6">
            <div className="max-w-4xl" style={{ fontFamily: 'Poppins, sans-serif' }}>
              <h2 className="text-4xl sm:text-5xl lg:text-6xl font-medium text-white leading-tight tracking-tight">
                Designed for Automation.
                <br className="hidden sm:block" />
                Powered by <span className="text-[#1D4ED8]">AI</span><span className="text-white">.</span>
              </h2>
              <div className="mt-6 space-y-1">
                <p className="text-white/80 text-base sm:text-lg">
                  Unlock the full potential of your business logic with FlowMind AI's node-based execution engine.
                </p>
                <p className="text-white/70 text-base sm:text-lg">
                  Explore new dimensions of productivity.
                </p>
              </div>
            </div>
            <div className="hidden md:block flex-shrink-0">
              <Image
                src="/assets/feature/Grid.svg"
                alt="Grid Icon"
                width={160}
                height={160}
                className="w-[140px] h-[140px] lg:w-[160px] lg:h-[160px]"
              />
            </div>
          </div>
        </motion.div>
        
        {/* Asymmetric 2x2 layout: left narrow, right wide (repeated for row 2) */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <FeatureCard key={index} feature={feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
};

export default Features;
