import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ErdPanel } from '../components/workspace/panels/ErdPanel';
import { AppMetadata } from '../types';

beforeEach(() => {
  (globalThis as any).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe('ErdPanel Component', () => {
  const mockApp: AppMetadata = {
    app_name: 'car_rental',
    title: 'Car Rental',
    modules: ['Fleet'],
    roles: ['Fleet Manager', 'System Manager'],
    doctypes: [
      {
        name: 'Vehicle',
        module: 'Fleet',
        fields: [
          { fieldname: 'license_plate', label: 'License Plate', fieldtype: 'Data', reqd: true },
        ],
        permissions: [
          { role: 'System Manager', read: true, write: true, create: true, delete: true },
        ],
      },
      {
        name: 'Rental Booking',
        module: 'Fleet',
        fields: [
          { fieldname: 'customer', label: 'Customer', fieldtype: 'Data', reqd: true },
          { fieldname: 'vehicle', label: 'Vehicle', fieldtype: 'Link', options: 'Vehicle' },
        ],
        permissions: [
          { role: 'System Manager', read: true, write: true, create: true, delete: true },
        ],
      },
    ],
    workflows: [],
  };

  it('renders empty message when no doctypes exist', () => {
    render(<ErdPanel app={null} />);
    expect(screen.getByText(/No data model yet/)).toBeDefined();
  });

  it('renders toolbar with auto layout and add doctype buttons', () => {
    render(<ErdPanel app={mockApp} />);
    expect(screen.getByText('Data Model (ERD)')).toBeDefined();
    expect(screen.getByText(/2 DocTypes/)).toBeDefined();
    expect(screen.getByText('Auto Layout')).toBeDefined();
    expect(screen.getByText('Add DocType')).toBeDefined();
  });

  it('opens add doctype modal and creates a new doctype via onUpdateApp', () => {
    const handleUpdate = vi.fn();
    render(<ErdPanel app={mockApp} onUpdateApp={handleUpdate} />);

    fireEvent.click(screen.getByText('Add DocType'));
    expect(screen.getByText('Add New DocType')).toBeDefined();

    const input = screen.getByPlaceholderText('e.g. Maintenance Log');
    fireEvent.change(input, { target: { value: 'Maintenance Log' } });

    fireEvent.click(screen.getByText('Create DocType'));
    expect(handleUpdate).toHaveBeenCalledTimes(1);
    const updatedApp: AppMetadata = handleUpdate.mock.calls[0][0];
    expect(updatedApp.doctypes.length).toBe(3);
    expect(updatedApp.doctypes[2].name).toBe('Maintenance Log');
  });
});
