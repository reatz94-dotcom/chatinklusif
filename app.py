
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import { ChatMessage, ChatMessageType } from './types';
import { sendMessageToGemini, textToSpeech, playAudioBuffer } from './services/geminiService';
import { AUDIO_SAMPLE_RATE_OUTPUT, AUDIO_NUM_CHANNELS } from './constants';
import { decodeAudioData, decode } from './services/audioUtils';

// Helper function to detect keywords
const containsKeywords = (text: string, keywords: string[]): boolean => {
  const lowerText = text.toLowerCase();
  return keywords.some(keyword => lowerText.includes(keyword.toLowerCase()));
};

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const audioBuffersRef = useRef<Map<string, AudioBuffer>>(new Map()); // Store generated audio buffers
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);

  // Initialize AudioContext on mount
  useEffect(() => {
    // FIX: Remove deprecated webkitAudioContext, as AudioContext is now widely supported.
    audioContextRef.current = new AudioContext({ sampleRate: AUDIO_SAMPLE_RATE_OUTPUT });
    return () => {
      // Clean up audio context on unmount
      audioContextRef.current?.close();
    };
  }, []);

  const handleSendMessage = useCallback(async (text: string) => {
    const userMessage: ChatMessage = {
      id: uuidv4(),
      sender: ChatMessageType.USER,
      text: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      let modelType: 'flash-lite' | 'flash-search' | 'pro-thinking' = 'flash-lite';
      const searchKeywords = ['terbaru', 'berita', 'fakta', 'siapa', 'dimana', 'kapan', 'saat ini', 'update', 'informasi terkini'];
      const complexKeywords = ['analisis', 'strategi komprehensif', 'desain pembelajaran universal', 'mendalam', 'bagaimana menerapkan', 'kompleks', 'tantangan'];

      if (containsKeywords(text, searchKeywords)) {
        modelType = 'flash-search';
      } else if (containsKeywords(text, complexKeywords) || text.length > 100) { // Simple heuristic for longer, complex queries
        modelType = 'pro-thinking';
      }

      const geminiResponse = await sendMessageToGemini(text, modelType);

      const botMessage: ChatMessage = {
        id: uuidv4(),
        sender: ChatMessageType.BOT,
        text: geminiResponse.text,
        timestamp: new Date(),
        sources: geminiResponse.sources,
      };

      // Generate TTS audio
      try {
        const audioBuffer = await textToSpeech(geminiResponse.text);
        audioBuffersRef.current.set(botMessage.id, audioBuffer);
        // Only set audioBlob if generation was successful
        botMessage.audioBlob = new Blob([], { type: 'audio/pcm' }); // Placeholder blob to indicate audio is available
      } catch (audioError) {
        console.error("Failed to generate TTS audio:", audioError);
        // Continue without audio if TTS fails
      }

      setMessages((prev) => [...prev, botMessage]);

    } catch (error: any) {
      console.error("Error sending message to Gemini:", error);
      const errorMessage: ChatMessage = {
        id: uuidv4(),
        sender: ChatMessageType.ERROR,
        text: `Terjadi kesalahan: ${error.message || 'Tidak dapat menghubungi AI.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, []); // eslint-disable-next-line react-hooks/exhaustive-deps

  const handlePlayAudio = useCallback(async (messageId: string) => {
    const messageToPlay = messages.find(msg => msg.id === messageId);
    if (!messageToPlay || !audioContextRef.current) return;

    const audioBuffer = audioBuffersRef.current.get(messageId);

    if (audioBuffer) {
      // Stop any currently playing audio and update its state
      setMessages(prevMessages => prevMessages.map(msg =>
        msg.audioPlaying ? { ...msg, audioPlaying: false } : msg
      ));

      // Create a new source for playback
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);

      source.onended = () => {
        setMessages(prevMessages =>
          prevMessages.map(msg =>
            msg.id === messageId ? { ...msg, audioPlaying: false } : msg
          )
        );
        audioSourceRef.current = null;
      };

      audioSourceRef.current = source;
      source.start(0);

      setMessages(prevMessages =>
        prevMessages.map(msg =>
          msg.id === messageId ? { ...msg, audioPlaying: true } : msg
        )
      );
    } else {
      console.warn(`Audio buffer not found for message ID: ${messageId}`);
    }
  }, [messages]);

  const handleStopAudio = useCallback((messageId: string) => {
    if (audioSourceRef.current) {
      try {
        audioSourceRef.current.stop();
        audioSourceRef.current = null;
        setMessages(prevMessages =>
          prevMessages.map(msg =>
            msg.id === messageId ? { ...msg, audioPlaying: false } : msg
          )
        );
      } catch (error) {
        console.error("Error stopping audio source:", error);
      }
    }
  }, []);

  // Initial welcome message
  useEffect(() => {
    const welcomeMessage: ChatMessage = {
      id: uuidv4(),
      sender: ChatMessageType.BOT,
      text: "Halo! Saya adalah chatbot pendamping yang akan membantu Anda memahami dan menerapkan prinsip Universal Design for Learning (UDL) untuk anak berkebutuhan khusus. Apa yang ingin Anda tanyakan hari ini?",
      timestamp: new Date(),
    };
    setMessages([welcomeMessage]);

    // Pre-generate welcome message audio
    const generateWelcomeAudio = async () => {
      try {
        const audioBuffer = await textToSpeech(welcomeMessage.text);
        audioBuffersRef.current.set(welcomeMessage.id, audioBuffer);
        setMessages(prev => prev.map(msg => msg.id === welcomeMessage.id ? { ...msg, audioBlob: new Blob([], { type: 'audio/pcm' }) } : msg));
      } catch (error) {
        console.error("Failed to pre-generate welcome message audio:", error);
      }
    };
    generateWelcomeAudio();
  }, []); // eslint-disable-next-line react-hooks/exhaustive-deps


  return (
    <div className="flex flex-col h-full w-full bg-gradient-to-br from-blue-100 to-indigo-200">
      <header className="bg-blue-600 text-white p-4 text-center text-2xl font-bold shadow-md">
        Chatbot UDL Inklusi
      </header>
      <ChatWindow messages={messages} onPlayAudio={handlePlayAudio} onStopAudio={handleStopAudio} />
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}

export default App;
