import { NextRequest, NextResponse } from 'next/server';

// Product categories are defined as a backend enum (ProductCategory).
// They cannot be created/updated/deleted dynamically.
// These endpoints return appropriate messages.

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  return NextResponse.json(
    {
      succeeded: false,
      message: 'Product categories are predefined and cannot be modified. Use the backend admin to manage categories.',
      errors: [{ message: 'Categories are read-only' }],
    },
    { status: 400 }
  );
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  return NextResponse.json(
    {
      succeeded: false,
      message: 'Product categories are predefined and cannot be deleted.',
      errors: [{ message: 'Categories are read-only' }],
    },
    { status: 400 }
  );
}
