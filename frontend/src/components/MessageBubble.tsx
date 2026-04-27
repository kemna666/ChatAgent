import { Message } from '../types';
import MarkdownIt from 'markdown-it';
import DOMPurify from 'dompurify';
import { useMemo } from 'react';
import { FiTrash2 } from 'react-icons/fi';
import { useLanguage } from '../contexts/LanguageContext';

interface MessageBubbleProps {
  message: Message;
  onDelete?: (message: Message) => void;
  deleting?: boolean;
}

export default function MessageBubble({ message, onDelete, deleting = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const { t } = useLanguage();
  const canDelete = Boolean(onDelete && message.id && !message.ephemeral);

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
    <div className={`group flex items-end gap-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && canDelete && (
        <button
          onClick={() => onDelete?.(message)}
          disabled={deleting}
          title={t('deleteMessage')}
          className="rounded-full border border-gray-200 bg-white p-2 text-gray-500 opacity-0 shadow-sm transition hover:border-red-200 hover:text-red-500 group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiTrash2 size={14} />
        </button>
      )}
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
      {isUser && canDelete && (
        <button
          onClick={() => onDelete?.(message)}
          disabled={deleting}
          title={t('deleteMessage')}
          className="rounded-full border border-gray-200 bg-white p-2 text-gray-500 opacity-0 shadow-sm transition hover:border-red-200 hover:text-red-500 group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiTrash2 size={14} />
        </button>
      )}
    </div>
  );
}
