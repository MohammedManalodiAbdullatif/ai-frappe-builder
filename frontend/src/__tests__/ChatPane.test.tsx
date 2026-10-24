import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ChatPane } from '../components/chat/ChatPane';
import { InterviewQuestion } from '../types';

describe('ChatPane Component', () => {
  it('renders empty chat state with example prompts when no messages', () => {
    const handleSend = vi.fn();
    render(
      <ChatPane
        stage="discovery"
        messages={[]}
        activeQuestion={null}
        hasArtifacts={false}
        isWorkspaceOpen={false}
        onToggleWorkspace={vi.fn()}
        onSendMessage={handleSend}
        isProcessing={false}
        isStreaming={false}
      />
    );

    expect(screen.getByText('What are you building?')).toBeDefined();
    expect(screen.getByText('Vehicle rental business')).toBeDefined();

    fireEvent.click(screen.getByText('Vehicle rental business'));
    expect(handleSend).toHaveBeenCalledWith('Vehicle rental business');
  });

  it('renders message rows and questionnaire dialogue box with option pills', () => {
    const handleSend = vi.fn();
    const q: InterviewQuestion = {
      id: 'q1',
      question: 'What is your rental pricing model?',
      reason: 'Determines rate fields in schema',
      options: ['Daily Rate', 'Hourly Rate'],
    };

    render(
      <ChatPane
        stage="discovery"
        messages={[
          { id: '1', role: 'user', content: 'I need a rental app', timestamp: '10:00' },
          { id: '2', role: 'assistant', content: 'Great, let me configure that.', timestamp: '10:01' },
        ]}
        activeQuestion={q}
        hasArtifacts={false}
        isWorkspaceOpen={false}
        onToggleWorkspace={vi.fn()}
        onSendMessage={handleSend}
        isProcessing={false}
        isStreaming={false}
      />
    );

    expect(screen.getByText('I need a rental app')).toBeDefined();
    expect(screen.getByText('Great, let me configure that.')).toBeDefined();
    expect(screen.getByText('What is your rental pricing model?')).toBeDefined();
    expect(screen.getByText('Determines rate fields in schema')).toBeDefined();
    expect(screen.getByText('Daily Rate')).toBeDefined();

    fireEvent.click(screen.getByText('Daily Rate'));
    expect(handleSend).toHaveBeenCalledWith('Daily Rate');
  });
});
