import { Message } from '../types';
import MarkdownIt from 'markdown-it';
import DOMPurify from 'dompurify';
import { useMemo } from 'react';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const htmlContent = useMemo(() => {
    if (isUser) {
      // 用户消息不处理markdown，直接返回纯文本
      return message.content;
    }

    // AI消息处理markdown
    const md = new MarkdownIt({
      html: false,
      linkify: true,
      breaks: true,
    });

    // 生成HTML
    const rawHtml = md.render(message.content);

    // 使用DOMPurify清理HTML，防止XSS
    const cleanHtml = DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 'code', 'pre', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'img', 'span', 'div', 'hr'
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'title', 'class'],
    });

    return cleanHtml;
  }, [message.content, isUser]);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-none'
            : 'bg-gray-200 text-gray-900 rounded-bl-none'
        }`}
      >
        {isUser ? (
          <p className="text-sm lg:text-base break-words whitespace-pre-wrap">
            {message.content}
          </p>
        ) : (
          <div
            className="text-sm prose prose-sm dark:prose-invert max-w-none [&>*]:my-1 [&>p]:my-1 [&>pre]:my-2 [&>code]:px-1 [&>code]:py-0.5 [&>code]:bg-gray-300 [&>code]:rounded [&>pre]:bg-gray-300 [&>pre]:p-2 [&>pre]:rounded [&>ul]:my-1 [&>ol]:my-1 [&>blockquote]:my-1 [&>h1]:my-2 [&>h2]:my-2 [&>h3]:my-1 [&>a]:text-blue-600 [&>a]:underline hover:[&>a]:text-blue-800"
            dangerouslySetInnerHTML={{ __html: htmlContent }}
          />
        )}
      </div>
    </div>
  );
}
