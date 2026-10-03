# intratexxxt v1 format

This is everything you need to write your own solver or verifier without touching the binary.
`verify.py` is a full reimplementation of the staircase in about 100 lines of standard-library
Python, and it is the reference if this document and the code ever disagree.

## Notation

| Symbol | Meaning |
|--------|---------|
| `i` | stage index, 0, 1, 2, ... |
| `S_i` | public state at stage `i`, 32 bytes |
| `x_i` | a solution (nonce) for stage `i` |
| `H` | SHA-256 |
| `d` | difficulty, in leading zero bits (`challenge.json` → `difficulty`) |
| `T` | target, `2^(256-d)` |
| `‖` | byte concatenation |

## The staircase

Every integer is a fixed-width 8-byte unsigned big-endian value (`u64be`). States are raw 32-byte
strings, not hex. Labels are ASCII with no terminator.

```
valid(i, S_i, x)  ⇔  integer( H("RCP|puzzle|" ‖ u64be(i) ‖ S_i ‖ u64be(x)) ) < T
S_(i+1)           =  H("RCP|next|"   ‖ u64be(i) ‖ S_i ‖ u64be(x_i))
```

`integer(...)` reads the 32-byte digest as a big-endian unsigned integer, so `< 2^(256-d)` is the
same as "the first `d` bits of the digest are zero". `S_0` is `challenge.json` → `stage0`.

The two labels are domain separators. The hash that *tests* a nonce and the hash that *produces*
the next state are never the same computation, so a valid puzzle hash tells you nothing about
`S_(i+1)` until you compute it.

There is no terminal stage. If stage `i` is solved, the rule above defines stage `i+1`, for every
finite `i`. Nothing is pre-generated and nothing is stored: the binary carries the rule, not a list.

### Canonical chain

Any `x` with `valid(i, S_i, x)` advances the stage, and different solutions lead to different
`S_(i+1)`. The **canonical chain** always takes the *smallest* valid `x ≥ 0`. The bundled miner and
`verify.py solve` both do this, so two people who solve honestly get byte-identical transcripts.
`data/ledger.json` is the canonical chain as far as it has been published.

### Worked example (stage 0 of the live challenge)

```
S_0 = d9ebb86837faf5ee5935b61a2957de6881b79363772aca66e2b4618732c3ab6f
d   = 26
```

Check it with `python verify.py stage 0 <S_0> <x_0>`. It prints `S_1` if `x_0` is valid. `x_0` is
the first entry of `data/ledger.json`.

## challenge.json

```jsonc
{
  "format": "rcp-challenge-v1",
  "name": "intratexxxt",
  "hash": "sha256",            // H
  "encoding": "u64be",         // integer encoding inside H
  "stage0": "<64 hex>",        // S_0, 256 random bits
  "difficulty": 26,            // d
  "lock": {
    "kdf": "argon2id",         // RFC 9106, version 0x13
    "memory_kib": 524288,
    "time": 3,
    "threads": 4,
    "key_len": 32,
    "salt": "<32 hex>",
    "cipher": "aes-256-gcm",   // NIST SP 800-38D, 96-bit nonce, 128-bit tag appended
    "nonce": "<24 hex>",
    "aad": "<hex>",            // "RCP|aad|v1|" ‖ commitment
    "ciphertext": "<hex>"
  },
  "commitment": "<64 hex>"     // H("RCP|commit|" ‖ token)
}
```

`intratexxxt open <string>` derives `Argon2id(<string>, salt, memory_kib, time, threads, key_len)`
and tries the result as the AES-256-GCM key over `ciphertext` with `nonce` and `aad`. GCM is
authenticated, so a wrong key fails cleanly. It never produces a plausible-looking wrong
plaintext.

## The payload

A genuine plaintext has exactly this shape:

```
RCP-SUCCESS-v1\n ‖ <message> ‖ \nverification-token: ‖ <64 hex>
```

The token is 256 random bits chosen when the lock was sealed. It appears nowhere else.
`H("RCP|commit|" ‖ token_bytes)` must equal `commitment`. That's how anyone can check an opening
without trusting the person who claims it, or the binary.

## progress.json (transcripts)

```jsonc
{
  "format": "rcp-progress-v1",
  "stage0": "<64 hex>",
  "difficulty": 26,
  "steps": [
    { "i": 0, "state": "<S_0 hex>", "nonce": 12345, "next": "<S_1 hex>" },
    ...
  ]
}
```

A transcript is valid if every step chains (`steps[k].state` is the previous `next`, `steps[k].i == k`),
every nonce meets the target, and every `next` is recomputed exactly. Both `intratexxxt verify` and
`python verify.py transcript` check all three.
