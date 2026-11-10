import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "../src/App.js";

afterEach(cleanup);

describe("App", () => {
  it("renders the translated back-office title", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("yafohi · Back-office");
  });
});
