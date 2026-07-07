type ThemeParams = {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
};

type TelegramWebApp = {
  initData: string;
  platform: string;
  colorScheme: "light" | "dark";
  themeParams: ThemeParams;
  ready: () => void;
  expand: () => void;
  openLink: (url: string) => void;
  HapticFeedback?: {
    notificationOccurred: (type: "error" | "success" | "warning") => void;
    impactOccurred: (style: "light" | "medium" | "heavy") => void;
  };
  LocationManager?: TelegramLocationManager;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

export type TelegramLocation = {
  latitude: number;
  longitude: number;
  horizontal_accuracy?: number;
  altitude?: number;
  vertical_accuracy?: number;
  course?: number;
  course_accuracy?: number;
  speed?: number;
  speed_accuracy?: number;
};

type TelegramLocationManager = {
  isInited: boolean;
  isLocationAvailable: boolean;
  isAccessRequested: boolean;
  isAccessGranted: boolean;
  init: (callback?: () => void) => void;
  getLocation: (callback: (location: TelegramLocation | null) => void) => void;
  openSettings?: () => void;
};

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

export function getTelegramInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}

export function initializeTelegramShell(): void {
  const webApp = getTelegramWebApp();
  if (!webApp) {
    return;
  }

  webApp.ready();
  webApp.expand();
}

export function notifyTelegram(type: "error" | "success" | "warning"): void {
  getTelegramWebApp()?.HapticFeedback?.notificationOccurred(type);
}

export function impactTelegram(style: "light" | "medium" | "heavy" = "light"): void {
  getTelegramWebApp()?.HapticFeedback?.impactOccurred(style);
}

export function openExternalUrl(url: string): void {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.openLink(url);
    return;
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

export function getTelegramLocationManager(): TelegramLocationManager | null {
  return getTelegramWebApp()?.LocationManager ?? null;
}

export function openTelegramLocationSettings(): boolean {
  const locationManager = getTelegramLocationManager();
  if (typeof locationManager?.openSettings !== "function") {
    return false;
  }

  locationManager.openSettings();
  return true;
}
