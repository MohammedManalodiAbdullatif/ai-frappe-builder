import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { Message } from '../components/chat/Message';
import { QuestionCard } from '../components/chat/QuestionCard';
import { InterviewTurn, Message as MessageType } from '../types';

describe('QuestionCard Component and Interview Turn Rendering', () => {
  it('renders an interview_turn event as exactly one assistant row and one QuestionCard (snapshot)', () => {
    const handleAnswer = vi.fn();
    const interviewTurn: InterviewTurn = {
      kind: 'question',
      say: 'Got it — a clinic with three branches.',
      question: {
        id: 'app_purpose',
        phase: 'basics',
        text: 'What should this app mainly help with?',
        help: 'Guides the core DocTypes and required functionality',
        input: 'single',
        options: [
          {
            value: 'operations_tracking',
            label: 'Operations & tracking',
            description: 'Daily operational logs, assets, and patient tracking',
          },
          {
            value: 'approvals_workflows',
            label: 'Approvals & workflows',
            description: 'Review cycles, prescription approvals, and sign-offs',
          },
        ],
        allow_custom: true,
      },
      assumptions: ['Medical clinic with 3 branches'],
      coverage: { basics: 0.17, domain: 0.0 },
    };

    const message: MessageType = {
      id: 'turn-msg-1',
      role: 'assistant',
      content: interviewTurn.say,
      timestamp: '12:00',
      interview_turn: interviewTurn,
    };

    const { container } = render(
      <Message
        message={message}
        onAnswerQuestion={handleAnswer}
        isLatestTurn={true}
        isProcessing={false}
      />
    );

    // Exactly one assistant message row
    const assistantRows = screen.getAllByTestId('assistant-message-row');
    expect(assistantRows).toHaveLength(1);

    // Exactly one QuestionCard
    const questionCards = screen.getAllByTestId('question-card');
    expect(questionCards).toHaveLength(1);

    // Renders the 'say' text, not raw markdown asterisks or options in the say text
    expect(screen.getByText('Got it — a clinic with three branches.')).toBeDefined();

    // Renders the question header and phase chip
    expect(screen.getByText('What should this app mainly help with?')).toBeDefined();
    expect(screen.getByText('Basics')).toBeDefined();

    // Renders the options
    expect(screen.getByText('Operations & tracking')).toBeDefined();
    expect(screen.getByText('Approvals & workflows')).toBeDefined();
    expect(screen.getByText('Something else…')).toBeDefined();

    // Snapshot matches
    expect(container).toMatchSnapshot();
  });

  it('answering collapses the card and sends the label as user message', () => {
    const handleAnswer = vi.fn();
    const interviewTurn: InterviewTurn = {
      kind: 'question',
      say: 'Understood.',
      question: {
        id: 'existing_erpnext',
        phase: 'basics',
        text: 'Are you already running ERPNext, or will this be a fresh Frappe site?',
        help: 'Determines whether to link standard ERPNext DocTypes',
        input: 'yesno',
        options: [
          { value: 'yes', label: 'Already running ERPNext' },
          { value: 'no', label: 'Fresh Frappe site' },
        ],
        allow_custom: false,
      },
      assumptions: [],
      coverage: { basics: 0.5, domain: 0.0 },
    };

    // Initially active question
    const { rerender } = render(
      <QuestionCard
        question={interviewTurn.question!}
        onAnswer={handleAnswer}
        answered={false}
      />
    );

    expect(screen.getByText('Are you already running ERPNext, or will this be a fresh Frappe site?')).toBeDefined();
    expect(screen.getByText('Already running ERPNext')).toBeDefined();
    expect(screen.getByText('Fresh Frappe site')).toBeDefined();

    // User clicks an option
    fireEvent.click(screen.getByText('Already running ERPNext'));
    expect(handleAnswer).toHaveBeenCalledWith('Already running ERPNext');

    // After answering, rerender in collapsed state
    rerender(
      <QuestionCard
        question={interviewTurn.question!}
        onAnswer={handleAnswer}
        answered={true}
        answerText="Already running ERPNext"
      />
    );

    // Card collapses to one line with checkmark and label
    expect(screen.getByTestId('question-card-collapsed')).toBeDefined();
    expect(screen.getByText('Already running ERPNext')).toBeDefined();
    expect(screen.queryByText('Fresh Frappe site')).toBeNull();
  });

  it('multi-select mode allows selecting checkboxes and submitting with Continue button', () => {
    const handleAnswer = vi.fn();
    const multiQuestion = {
      id: 'primary_users',
      phase: 'basics' as const,
      text: 'Who will use it day to day?',
      help: 'Defines user roles',
      input: 'multi' as const,
      options: [
        { value: 'front_desk', label: 'Front desk' },
        { value: 'doctors', label: 'Doctors' },
        { value: 'admin', label: 'Admin staff' },
      ],
      allow_custom: true,
    };

    render(<QuestionCard question={multiQuestion} onAnswer={handleAnswer} />);

    // Checkboxes
    const frontDeskCheckbox = screen.getByLabelText(/Front desk/i);
    const doctorsCheckbox = screen.getByLabelText(/Doctors/i);

    fireEvent.click(frontDeskCheckbox);
    fireEvent.click(doctorsCheckbox);

    const continueBtn = screen.getByText('Continue');
    fireEvent.click(continueBtn);

    expect(handleAnswer).toHaveBeenCalledWith('Front desk, Doctors');
  });
});
