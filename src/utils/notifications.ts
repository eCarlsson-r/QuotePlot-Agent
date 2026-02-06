export const requestNotificationPermission = async () => {
  if (!("Notification" in window)) {
    console.log("This browser does not support desktop notification");
    return;
  }

  if (Notification.permission !== "granted") {
    await Notification.requestPermission();
  } else {
    new Notification("🎯 Lucy Alerts Active", { body: "You will now receive high-confidence trade signals." });
  }
};