export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: Message[];
}

export interface ChatResponse {
  messages: Message[];
}

export interface StreamResponse {
  content: string;
  done: boolean;
}

export interface UserResponse {
  id: string;
  email: string;
  token: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface SessionResponse {
  session_id: string;
  name: string;
  token: string;
}

export interface UserCreate {
  username: string;
  email: string;
  passwd: string;
}

export interface Session {
  id: string;
  name: string;
  token: string;
  created_at?: string;
}
