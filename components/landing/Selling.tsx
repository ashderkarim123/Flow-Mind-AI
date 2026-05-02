"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useAuth } from "@/lib/AuthContext";
import { useRouter } from "next/navigation";

const Selling = () => {
  const { user } = useAuth();
  const router = useRouter();

  const handleGetStarted = () => {
    if (user) {
      router.push('/workflows');
    } else {
      router.push('/sign-in');
    }
  };

  return (
    <section className="relative py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          {/* <h2 
            className="text-4xl sm:text-5xl font-medium text-white mb-4" 
            style={{ fontFamily: 'Poppins, sans-serif' }}
          >
            Selling
          </h2> */}
        </motion.div>
        
        {/* Selling card */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          viewport={{ once: true }}
          className="max-w-5xl mx-auto"
        >
          <div className="bg-[#000000] rounded-2xl p-8 flex flex-col lg:flex-row items-center gap-8 h-80" style={{
            borderTop: '3px solid #393F40',
            borderBottom: '3px solid #393F40',
            borderLeft: '0.5px solid #393F40',
            borderRight: '0.5px solid #393F40'
          }}>
            {/* Left side - Content */}
            <div className="flex-1 flex flex-col justify-between h-full">
              <div>
                <h3 className="text-4xl sm:text-5xl font-medium text-white mb-4" style={{ fontFamily: 'Poppins, sans-serif' }}>
                  Start Building Now
                </h3>
                <p className="text-zinc-400 text-base leading-relaxed mb-6" style={{ fontFamily: 'Poppins, sans-serif' }}>
                  Ready to automate your logic? Jump into the FlowMind AI workflow builder and connect your first AI node. It's fast, interactive, and completely drag-and-drop.
                </p>
              </div>
              <div className="mt-auto">
                <button onClick={handleGetStarted}
                  className="bg-[#161616] hover:bg-[#2A2A2A] text-white px-6 py-3 rounded-full font-medium transition-all duration-300 border border-[#312F2F] hover:border-[#4A4A4A] hover:shadow-lg hover:scale-105"
                  style={{ fontFamily: 'Poppins, sans-serif' }}
                >
                  Build a Workflow
                </button>
              </div>
            </div>
            
            {/* Right side - Image */}
            <div className="flex-1 lg:max-w-md">
              <div className="pl-60 h-64 md:h-72 lg:h-80 overflow-hidden">
                <Image
                  src="/assets/selling/Image.svg"
                  alt="Selling Image"
                  width={400}
                  height={300}
                  className="w-full h-full object-fill"
                />
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Selling;
