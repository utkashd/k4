export function isDevelopmentEnvironment(): boolean {
    return getEnvironment() === K4Environment.Development;
}

export function isProductionEnvironment(): boolean {
    return getEnvironment() === K4Environment.Production;
}

enum K4Environment {
    Development,
    Production,
}

export function getEnvironment(): K4Environment {
    if (import.meta.env.VITE_K4_ENVIRONMENT === "development") {
        return K4Environment.Development;
    }
    return K4Environment.Production;
}

export function isInContainer(): boolean {
    return import.meta.env.VITE_IN_CONTAINER === "true";
}
