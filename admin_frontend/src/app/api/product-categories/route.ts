import { NextResponse } from 'next/server';

const PRODUCT_CATEGORIES = [
  { id: 'cake', title: 'Cake', description: 'Cakes and layered pastries' },
  { id: 'pastry', title: 'Pastry', description: 'Puff pastries and filo items' },
  { id: 'cookie', title: 'Cookie', description: 'Cookies and biscuits' },
  { id: 'bread', title: 'Bread', description: 'Breads and flatbreads' },
  { id: 'sweet', title: 'Sweet', description: 'Traditional Afghan sweets' },
  { id: 'drink', title: 'Drink', description: 'Beverages and teas' },
  { id: 'other', title: 'Other', description: 'Other items' },
];

export async function GET() {
  return NextResponse.json({
    succeeded: true,
    message: 'Success',
    data: PRODUCT_CATEGORIES,
  });
}
