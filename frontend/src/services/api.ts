import axios, { AxiosInstance } from 'axios';
import { Message, SessionResponse, UserCreate } from '../types';

const API_BASE_URL = '/api/v1';

class ApiService {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.loadTokenFromStorage();
    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      // FormData时，删除固定的Content-Type，让浏览器自动设置
      if (config.data instanceof FormData) {
        delete config.headers['Content-Type'];
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  private loadTokenFromStorage() {
    this.token = localStorage.getItem('access_token');
  }

  private saveTokenToStorage(token: string) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('session_id');
    localStorage.removeItem('session_token');
  }

  // Auth endpoints
  async register(userData: UserCreate) {
    const response = await this.client.post('/auth/register', userData);
    this.saveTokenToStorage(response.data.token);
    return response.data;
  }

  async login(email: string, password: string) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.client.post('/auth/login', formData);
    this.saveTokenToStorage(response.data.access_token);
    return response.data;
  }

  // Session endpoints
  async createSession(sessionName: string): Promise<SessionResponse> {
    const response = await this.client.post(`/auth/session?session_name=${encodeURIComponent(sessionName)}`);
    return response.data;
  }

  async getSessions(): Promise<SessionResponse[]> {
    const response = await this.client.get('/auth/sessions');
    return response.data;
  }

  async updateSessionName(sessionId: string, name: string): Promise<SessionResponse> {
    const formData = new FormData();
    formData.append('name', name);
    const response = await this.client.patch(`/auth/session/name?session_id=${sessionId}`, formData);
    return response.data;
  }

  async deleteSession(sessionId: string) {
    await this.client.delete(`/auth/session?session_id=${sessionId}`);
  }

  // Chat endpoints
  async sendChat(messages: Message[], sessionId: string) {
    const response = await this.client.post(`/chat/chat?session_id=${sessionId}`, {
      messages,
    });
    return response.data;
  }

  async streamChat(messages: Message[], sessionId: string): Promise<Response> {
    const response = await fetch(`${API_BASE_URL}/chat/chat/stream?session_id=${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
      },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      throw new Error('Stream chat failed');
    }

    return response;
  }

  async getMessages(sessionId: string) {
    const response = await this.client.get(`/chat/messages?session_id=${sessionId}`);
    return response.data;
  }

  async clearHistory(sessionId: string) {
    const response = await this.client.delete(`/chat/messages?session_id=${sessionId}`);
    return response.data;
  }

  async clearMemory(sessionId: string) {
    const response = await this.client.delete(`/chat/memory?session_id=${sessionId}`);
    return response.data;
  }

  async deleteMessage(sessionId: string, messageId: string) {
    const response = await this.client.delete(
      `/chat/message?session_id=${encodeURIComponent(sessionId)}&message_id=${encodeURIComponent(messageId)}`
    );
    return response.data;
  }

  async changePassword(oldPassword: string, newPassword: string) {
    const params = new URLSearchParams();
    params.append('old_passwd', oldPassword);
    params.append('new_passwd', newPassword);
    const response = await this.client.patch('/auth/passwd/change', params);
    this.saveTokenToStorage(response.data.token);
    return response.data;
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  getToken(): string | null {
    return this.token;
  }
}

export const apiService = new ApiService();
