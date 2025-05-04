"""
Chatbot AI logic for NetSpace
Uses Hugging Face transformers for free, local conversational AI.
Main models: DialoGPT-small for English, FLAN-T5 for multilingual support.

Install dependencies:
    pip install transformers torch sentencepiece
"""

from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatBot:
    """
    Enhanced DialoGPT chatbot with better context handling and response filtering.
    """
    def __init__(self, model_name='microsoft/DialoGPT-small', device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing DialoGPT on {self.device}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
        except Exception as e:
            logger.error(f"Failed to load model/tokenizer: {e}")
            raise RuntimeError(f"Failed to load model/tokenizer: {e}")
        self.max_history = 5
        self.max_length = 100
        self.bad_words = ['hate', 'kill', 'abuse']  # Add more if needed

    def filter_response(self, response: str) -> str:
        """Filter out potentially inappropriate content"""
        response = response.strip()
        if any(word in response.lower() for word in self.bad_words):
            return "I prefer to keep the conversation respectful."
        return response

    def get_response(self, message: str, history: Optional[List[str]] = None) -> str:
        """
        Generate a response using DialoGPT with improved context handling
        """
        try:
            # Prepare history window
            messages = history[-self.max_history:] if history else []
            input_text = ''
            for past_message in messages:
                input_text += past_message + self.tokenizer.eos_token
            input_text += message + self.tokenizer.eos_token

            # Encode and generate response
            input_ids = self.tokenizer.encode(input_text, return_tensors='pt').to(self.device)
            
            # Add parameters for better quality responses
            chat_history_ids = self.model.generate(
                input_ids,
                max_length=self.max_length,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=0.7,
                no_repeat_ngram_size=3
            )
            
            response = self.tokenizer.decode(chat_history_ids[:, input_ids.shape[-1]:][0], skip_special_tokens=True)
            return self.filter_response(response)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm having trouble processing that. Could you try rephrasing?"

class MultilingualBot:
    """
    Enhanced FLAN-T5 chatbot with better multilingual support and response quality
    """
    def __init__(self, model_name="google/flan-t5-base", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing FLAN-T5 on {self.device}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
        except Exception as e:
            logger.error(f"Failed to load FLAN-T5 model/tokenizer: {e}")
            raise RuntimeError(f"Failed to load FLAN-T5 model/tokenizer: {e}")
        
        self.max_length = 150
        self.bad_words = ['hate', 'kill', 'abuse']
        
        # Add system prompts for better responses
        self.system_prompts = {
            'greeting': 'You are a friendly and helpful AI assistant. ',
            'context': 'Given the context, provide a natural and helpful response. ',
            'error': 'I apologize, but I had trouble understanding that. Could you rephrase your question?'
        }
        self.personality = "Be concise, helpful, and friendly in your responses. "

    def filter_response(self, response: str) -> str:
        """Filter out potentially inappropriate content"""
        response = response.strip()
        if any(word in response.lower() for word in self.bad_words):
            return "I prefer to keep the conversation respectful."
        return response

    def format_prompt(self, message: str) -> str:
        """Format the input prompt for better responses"""
        # Add personality and context to the prompt
        prompt = (
            f"{self.system_prompts['greeting']}"
            f"{self.personality}"
            f"User message: {message}\n"
            f"Assistant response:"
        )
        return prompt

    def get_response(self, message: str) -> str:
        """
        Generate a response using FLAN-T5 with improved parameters
        """
        try:
            # Format prompt with better context
            input_text = self.format_prompt(message)
            input_ids = self.tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512).input_ids.to(self.device)
            
            # Generate with optimized parameters
            output = self.model.generate(
                input_ids,
                max_length=self.max_length,
                do_sample=True,
                top_k=40,  # Reduced for more focused responses
                top_p=0.90,  # Adjusted for better coherence
                temperature=0.8,  # Slightly increased for more natural responses
                no_repeat_ngram_size=3,
                num_return_sequences=1,
                length_penalty=1.0,  # Prefer slightly longer responses
                repetition_penalty=1.2  # Avoid repetitive text
            )
            
            response = self.tokenizer.decode(output[0], skip_special_tokens=True)
            response = self.clean_response(response)
            return self.filter_response(response)

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self.system_prompts['error']

    def clean_response(self, response: str) -> str:
        """Clean and format the response text"""
        response = response.strip()
        
        # Remove any "Assistant:" or similar prefixes
        prefixes = ["Assistant:", "AI:", "Response:"]
        for prefix in prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Ensure proper sentence capitalization
        if response and response[0].islower():
            response = response[0].upper() + response[1:]
            
        return response

def create_chatbot(choice: str = '1'):
    """Factory function to create the appropriate chatbot instance"""
    if choice == '1':
        return ChatBot(), "DialoGPT"
    elif choice == '2':
        return MultilingualBot(), "FLAN-T5"
    else:
        raise ValueError("Invalid choice. Please select 1 for DialoGPT or 2 for FLAN-T5.")

if __name__ == '__main__':
    print("Select chatbot engine:")
    print("1. DialoGPT (English, optimized for chat)")
    print("2. FLAN-T5 (Multilingual, good for various languages)")
    
    try:
        choice = input("Enter 1 or 2: ").strip()
        bot, model_name = create_chatbot(choice)
        print(f"[Using {model_name}]")
        print("Type 'exit' or 'quit' to end the conversation")
        
        history = []
        while True:
            user_input = input('You: ').strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input:
                continue
                
            if choice == '1':
                history.append(user_input)
                reply = bot.get_response(user_input, history=history)
                history.append(reply)
            else:
                reply = bot.get_response(user_input)
                
            print('Bot:', reply)
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print("An error occurred. Please try again.")
