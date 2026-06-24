import fs from "fs";
import path from "path";
import Dashboard, { Results } from "../components/Dashboard";

function readJson<T>(name: string, fallback: T): T {
  const file = path.join(process.cwd(), "..", "runs", name);
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

export default function Page() {
  const results = readJson<Results>("latest.json", {} as Results);
  const history = readJson("history.json", []);
  return <Dashboard results={{ ...results, history }} />;
}

