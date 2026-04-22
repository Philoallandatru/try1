import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  SkeletonBox,
  SkeletonText,
  SkeletonCard,
  SkeletonList,
  SkeletonTable,
  SkeletonPage,
} from './SkeletonLoader';

describe('SkeletonLoader Components', () => {
  describe('SkeletonBox', () => {
    it('renders with default dimensions', () => {
      const { container } = render(<SkeletonBox />);
      const box = container.querySelector('.skeleton-box');

      expect(box).toBeInTheDocument();
      expect(box).toHaveStyle({ width: '100%', height: '20px' });
    });

    it('renders with custom dimensions', () => {
      const { container } = render(<SkeletonBox width="200px" height="50px" />);
      const box = container.querySelector('.skeleton-box');

      expect(box).toHaveStyle({ width: '200px', height: '50px' });
    });
  });

  describe('SkeletonText', () => {
    it('renders default 3 lines', () => {
      const { container } = render(<SkeletonText />);
      const boxes = container.querySelectorAll('.skeleton-box');

      expect(boxes).toHaveLength(3);
    });

    it('renders custom number of lines', () => {
      const { container } = render(<SkeletonText lines={5} />);
      const boxes = container.querySelectorAll('.skeleton-box');

      expect(boxes).toHaveLength(5);
    });

    it('last line is shorter (60% width)', () => {
      const { container } = render(<SkeletonText lines={3} />);
      const boxes = container.querySelectorAll('.skeleton-box');
      const lastBox = boxes[boxes.length - 1];

      expect(lastBox).toHaveStyle({ width: '60%' });
    });
  });

  describe('SkeletonCard', () => {
    it('renders card structure', () => {
      const { container } = render(<SkeletonCard />);

      expect(container.querySelector('.skeleton-card')).toBeInTheDocument();
      expect(container.querySelector('.skeleton-card-content')).toBeInTheDocument();
    });

    it('contains image placeholder and text', () => {
      const { container } = render(<SkeletonCard />);
      const boxes = container.querySelectorAll('.skeleton-box');

      // Should have: 1 image box + 1 title box + 2 text lines
      expect(boxes.length).toBeGreaterThanOrEqual(4);
    });
  });

  describe('SkeletonList', () => {
    it('renders default 5 items', () => {
      const { container } = render(<SkeletonList />);
      const items = container.querySelectorAll('.skeleton-list-item');

      expect(items).toHaveLength(5);
    });

    it('renders custom number of items', () => {
      const { container } = render(<SkeletonList items={10} />);
      const items = container.querySelectorAll('.skeleton-list-item');

      expect(items).toHaveLength(10);
    });

    it('each item has avatar and content', () => {
      const { container } = render(<SkeletonList items={1} />);
      const item = container.querySelector('.skeleton-list-item');
      const boxes = item?.querySelectorAll('.skeleton-box');

      // Should have: 1 avatar + 2 content boxes
      expect(boxes).toHaveLength(3);
    });
  });

  describe('SkeletonTable', () => {
    it('renders default 5 rows and 4 columns', () => {
      const { container } = render(<SkeletonTable />);
      const rows = container.querySelectorAll('.skeleton-table-row');

      expect(rows).toHaveLength(5);

      const headerCells = container.querySelector('.skeleton-table-header')?.querySelectorAll('.skeleton-box');
      expect(headerCells).toHaveLength(4);
    });

    it('renders custom dimensions', () => {
      const { container } = render(<SkeletonTable rows={3} columns={6} />);
      const rows = container.querySelectorAll('.skeleton-table-row');

      expect(rows).toHaveLength(3);

      const headerCells = container.querySelector('.skeleton-table-header')?.querySelectorAll('.skeleton-box');
      expect(headerCells).toHaveLength(6);
    });

    it('each row has correct number of columns', () => {
      const { container } = render(<SkeletonTable rows={2} columns={3} />);
      const firstRow = container.querySelector('.skeleton-table-row');
      const cells = firstRow?.querySelectorAll('.skeleton-box');

      expect(cells).toHaveLength(3);
    });
  });

  describe('SkeletonPage', () => {
    it('renders page structure', () => {
      const { container } = render(<SkeletonPage />);

      expect(container.querySelector('.skeleton-page')).toBeInTheDocument();
      expect(container.querySelector('.skeleton-page-header')).toBeInTheDocument();
      expect(container.querySelector('.skeleton-page-content')).toBeInTheDocument();
    });

    it('contains header and multiple cards', () => {
      const { container } = render(<SkeletonPage />);
      const cards = container.querySelectorAll('.skeleton-card');

      expect(cards.length).toBeGreaterThanOrEqual(2);
    });
  });
});
