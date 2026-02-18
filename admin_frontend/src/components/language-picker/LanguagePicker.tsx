'use client';

import { Menu, ActionIcon, Tooltip } from '@mantine/core';
import { IconLanguage } from '@tabler/icons-react';
import { useState } from 'react';

type LanguagePickerProps = {
    type?: 'default' | 'collapsed';
};

const languages = [
    { code: 'en', label: 'English', flag: '🇬🇧' },
    { code: 'fa', label: 'Dari', flag: '🇦🇫' },
    { code: 'ps', label: 'Pashto', flag: '🇦🇫' },
];

const LanguagePicker = ({ type = 'default' }: LanguagePickerProps) => {
    const [selectedLanguage, setSelectedLanguage] = useState('en');

    const handleLanguageChange = (code: string) => {
        setSelectedLanguage(code);
        // TODO: Implement actual language change logic
        console.log('Language changed to:', code);
    };

    return (
        <Menu shadow="md" width={200}>
            <Menu.Target>
                <Tooltip label="Change Language">
                    <ActionIcon size="lg" variant="default">
                        <IconLanguage size={20} />
                    </ActionIcon>
                </Tooltip>
            </Menu.Target>

            <Menu.Dropdown>
                <Menu.Label>Select Language</Menu.Label>
                {languages.map((lang) => (
                    <Menu.Item
                        key={lang.code}
                        onClick={() => handleLanguageChange(lang.code)}
                        leftSection={<span style={{ fontSize: '1.2rem' }}>{lang.flag}</span>}
                        style={{
                            fontWeight: selectedLanguage === lang.code ? 600 : 400,
                            backgroundColor:
                                selectedLanguage === lang.code
                                    ? 'var(--mantine-color-gray-1)'
                                    : undefined,
                        }}
                    >
                        {lang.label}
                    </Menu.Item>
                ))}
            </Menu.Dropdown>
        </Menu>
    );
};

export default LanguagePicker;
