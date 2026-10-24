import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { LeftPanel } from '../components/LeftPanel';
import { InterviewQuestion } from '../types';

describe('LeftPanel Component', () => {
  it('renders conversational messages and stepper', () => {
    const messages = [
      { id: '1', role: 'assistant' as const, content: 'Hello user', timestamp: '10:00' },
      { id: '2', role: 'user' as const, content: 'I need a car rental app', timestamp: '10:01' },
    ];

    render(
      <LeftPanel
        stage="discovery"
        messages={messages}
        activeQuestion={null}
        assumptions={['USD currency']}
        archetype="car_rental"
        isProcessing={false}
        onSendMessage={vi.fn()}
      />
    );

    expect(screen.getByText('Hello user')).toBeDefined();
    expect(screen.getByText('I need a car rental app')).toBeDefined();
    expect(screen.getByText('USD currency')).toBeDefined();
    expect(screen.getByText('car_rental')).toBeDefined();
  });

  it('renders question options and allows clicking', () => {
    const handleSend = vi.fn();
    const q: InterviewQuestion = {
      id: 'q1',
      question: 'Do you charge daily?',
      reason: 'Pricing logic',
      options: [
        { label: 'Daily Rate', value: 'daily' },
        { label: 'Hourly Rate', value: 'hourly' },
      ],
    };

    render(
      <LeftPanel
        stage="discovery"
        messages={[]}
        activeQuestion={q}
        assumptions={[]}
        isProcessing={false}
        onSendMessage={handleSend}
      />
    );

    expect(screen.getByText('Do you charge daily?')).toBeDefined();
    const optionBtn = screen.getByText('Daily Rate');
    fireEvent.click(optionBtn);

    expect(handleSend).toHaveBeenCalledWith('daily');
  });
});
