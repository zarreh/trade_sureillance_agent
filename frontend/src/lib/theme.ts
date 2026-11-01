export const THEME_STORAGE_KEY = "theme";

// Runs in <head> before first paint: dark is the default, a stored "light" removes it.
export const THEME_INIT_SCRIPT = `(function(){try{if(localStorage.getItem("${THEME_STORAGE_KEY}")==="light")document.documentElement.classList.remove("dark")}catch(e){}})()`;
