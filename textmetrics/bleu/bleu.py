"""
Simply wraps the BLEU perl script (multi-bleu.perl).
"""

# builtins
import code
import os
import subprocess
import tempfile
from typing import List

# local
from common import Corpora, BLEUResults


def extract_res(raw_output: bytes) -> BLEUResults:
    """Turns raw output from multi-bleu.perl script into BLEUResults format."""
    output = str(raw_output)

    #
    # example:
    #
    # "b'BLEU = 100.00, 100.0/100.0/100.0/100.0 (BP=1.000, ratio=1.000, hyp_len=11, ref_len=11)\\n'"
    #

    s1, s2 = output.split('(')

    # handle s1: overall and bleu-1..4 scores
    overall_section, ngram_section = s1.split(',')
    overall = float(overall_section.split('=')[1].strip())
    subscores = [float(s) for s in ngram_section.strip().split('/')]

    # handle s2: the sore breakdown in parentheses
    s2_contents, _ = s2.split(')')
    s2_pieces = [piece.strip() for piece in s2_contents.split(',')]
    bp = float(s2_pieces[0].split('=')[1])
    len_ratio = float(s2_pieces[1].split('=')[1])
    can_len = int(s2_pieces[2].split('=')[1])
    ref_len = int(s2_pieces[3].split('=')[1])

    return {
        'overall': overall,
        'bleu1': subscores[0],
        'bleu2': subscores[1],
        'bleu3': subscores[2],
        'bleu4': subscores[3],
        'brevity_penalty': bp,
        'length_ratio': len_ratio,
        'candidate_length': can_len,
        'reference_length': ref_len,
    }


def runbleu(reference_fns: List[str], candidate_fn: str,
            script = 'textmetrics/bleu/multi-bleu.perl') -> BLEUResults:
    """Runs `script` to compute BLEU scores for the file name candidate_fn
    given reference filenames `reference_fns`."""
    with open(candidate_fn, 'r') as in_f:
        res = subprocess.run(
            ['perl', script] + reference_fns,
            stdin=in_f,
            stdout=subprocess.PIPE,
        )
    return extract_res(res.stdout)


def bleu(references: Corpora, candidates: Corpora) -> None:
    """Runs each of `candidates` against all `references` separately.

    Writes results into candidates['bleu'].
    """
    # Write all data to tmp files
    worklist = [references, candidates]
    for c in worklist:
        for corpus in c.values():
            tf = tempfile.NamedTemporaryFile(delete=False)
            tf.write(bytes(corpus['contents'], 'utf-8'))
            tf.close()
            corpus['tmpfile'] = tf.name

    # compute bleu for each candidate against all references
    ref_fns = [ref['tmpfile'] for ref in references.values()]
    for candidate in candidates.values():
        candidate['bleu'] = runbleu(ref_fns, candidate['tmpfile'])

    # cleanup tmp files
    for c in worklist:
        for corpus in c.values():
            os.remove(corpus['tmpfile'])
            corpus['tmpfile'] = None
