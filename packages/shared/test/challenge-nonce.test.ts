import assert from "node:assert/strict";
import { test } from "node:test";
import { ChallengeNonceRotator } from "../src/challenge-nonce";

test("ChallengeNonceRotator comeca com um nonce valido", () => {
  const rotator = new ChallengeNonceRotator();
  assert.match(rotator.current, /^[0-9a-f]{32}$/);
});

test("ChallengeNonceRotator.rotate troca o valor atual", () => {
  const rotator = new ChallengeNonceRotator();
  const before = rotator.current;
  const after = rotator.rotate();
  assert.notEqual(before, after);
  assert.equal(rotator.current, after);
});

test("ChallengeNonceRotator aceita um valor inicial customizado", () => {
  const rotator = new ChallengeNonceRotator("nonce-fixo-de-teste");
  assert.equal(rotator.current, "nonce-fixo-de-teste");
});
