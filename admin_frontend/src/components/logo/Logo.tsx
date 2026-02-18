import {
  Group,
  Text,
  UnstyledButton,
  UnstyledButtonProps,
} from '@mantine/core';
import Image from 'next/image';
import Link from 'next/link';

import classes from './Logo.module.css';

type LogoProps = {
  href?: string;
  showText?: boolean;
} & UnstyledButtonProps;

const Logo = ({ href, showText = true, ...others }: LogoProps) => {
  return (
    <UnstyledButton
      className={classes.logo}
      component={Link}
      href={href || '/'}
      {...others}
    >
      <Group gap="xs">
        <Image
          src="/logo-no-background.png"
          height={showText ? 32 : 24}
          width={showText ? 32 : 24}
          alt="Kabul Sweets logo"
        />
        {showText && (
          <Text fw={800}>
            Kabul <span style={{ color: '#ad751c' }}>Sweets</span> Admin
          </Text>
        )}
      </Group>
    </UnstyledButton>
  );
};

export default Logo;
