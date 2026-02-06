"use client";
import { useEffect, useState } from "react";

const Typewriter = ({ text, delay = 20, onComplete }: { text: string; delay?: number, onComplete?: () => void }) => {
  const [currentText, setCurrentText] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    let index = 0;
        const interval = setInterval(() => {
            setCurrentText(text.slice(0, index + 1));
            index++;
            
            if (index >= text.length) {
                clearInterval(interval);
                setDone(true);
            }
        }, delay);

        return () => clearInterval(interval);
  }, [delay, text]);

  useEffect(() => {
        if (done && onComplete) {
            onComplete();
        }
    }, [done, onComplete]);
    
  return <span>{currentText}</span>;
};

export default Typewriter;