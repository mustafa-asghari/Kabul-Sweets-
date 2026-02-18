import { useEffect, useState } from 'react';
import { Skeleton } from '@mantine/core';
import { apiGetBlob } from '@/lib/hooks/useApi';

interface AuthenticatedImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    src: string;
}

export function AuthenticatedImage({ src, alt, ...props }: AuthenticatedImageProps) {
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const blob = await apiGetBlob(src);
                const url = URL.createObjectURL(blob);
                if (active) {
                    setBlobUrl(url);
                    setLoading(false);
                }
            } catch (err) {
                if (active) {
                    setError(true);
                    setLoading(false);
                }
            }
        })();
        return () => {
            active = false;
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
    }, [src]);

    if (loading) return <Skeleton height="100%" width="100%" animate />;
    if (error) return <div style={{ background: '#f8f9fa', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#868e96' }}>Error loading image</div>;

    return <img src={blobUrl || ''} alt={alt} {...props} />;
}
