import { describe, expect, it } from "vitest";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { EKSPRESI } from "./Capy";
import { warnaSeksi } from "./Infografis";

describe("ekspresi Capy", () => {
  it("setiap ekspresi punya berkas gambar yang ada di folder public", () => {
    const publik = join(process.cwd(), "public");
    const hilang = Object.entries(EKSPRESI)
      .filter(([, e]) => !existsSync(join(publik, e.src)))
      .map(([nama, e]) => `${nama} -> ${e.src}`);
    expect(hilang).toEqual([]);
  });
  it("tidak ada dua ekspresi yang menunjuk ke gambar yang sama", () => {
    const sumber = Object.values(EKSPRESI).map((e) => e.src);
    expect(new Set(sumber).size).toBe(sumber.length);
  });
});

describe("warna seksi", () => {
  it("seksi yang sama selalu mendapat warna yang sama", () => {
    expect(warnaSeksi("Humas")).toBe(warnaSeksi("Humas"));
  });
});
