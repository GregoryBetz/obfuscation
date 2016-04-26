#include "thpool_fns.h"
#include "utils.h"

#include <stdlib.h>
#include <string.h>

#include <mmap/mmap.h>
#include <mmap/mmap_clt.h>
#include <mmap/mmap_gghlite.h>

void *
thpool_encode_elem(void *vargs)
{
    struct encode_elem_s *args = (struct encode_elem_s *) vargs;
    aes_randstate_t rand;

    aes_randinit(rand);
    args->vtable->enc->encode(args->enc, args->sk, args->n, args->plaintext,
                              args->group, rand);
    aes_randclear(rand);

    for (int i = 0; i < args->n; ++i)
        fmpz_clear(args->plaintext[i]);
    free(args->plaintext);
    free(args);

    return NULL;
}

void *
thpool_write_layer(void *vargs)
{
    char fname[1024];
    int fnamelen = 1024;
    FILE *fp;
    double end;
    struct write_layer_s *args = (struct write_layer_s *) vargs;

    (void) snprintf(fname, fnamelen, "%s/%ld.input", args->dir, args->idx);
    fp = fopen(fname, "w+b");
    if (fp == NULL) {
        fprintf(stderr, "Unable to write '%s'\n", fname);
        goto done;
    }
    fwrite(&args->inp, sizeof args->inp, 1, fp);
    fclose(fp);

    (void) snprintf(fname, fnamelen, "%s/%ld.nrows", args->dir, args->idx);
    fp = fopen(fname, "w+b");
    if (fp == NULL) {
        fprintf(stderr, "Unable to write '%s'\n", fname);
        goto done;
    }
    fwrite(&args->nrows, sizeof args->nrows, 1, fp);
    fclose(fp);

    (void) snprintf(fname, fnamelen, "%s/%ld.ncols", args->dir, args->idx);
    fp = fopen(fname, "w+b");
    if (fp == NULL) {
        fprintf(stderr, "Unable to write '%s'\n", fname);
        goto done;
    }
    fwrite(&args->ncols, sizeof args->ncols, 1, fp);
    fclose(fp);

    (void) snprintf(fname, fnamelen, "%s/%ld.zero", args->dir, args->idx);
    fp = fopen(fname, "w+b");
    if (fp == NULL) {
        fprintf(stderr, "Unable to write '%s'\n", fname);
        goto done;
    }
    for (long i = 0; i < args->nrows; ++i) {
        for (long j = 0; j < args->ncols; ++j) {
            args->vtable->enc->fwrite(args->zero_enc[0]->m[i][j], fp);
        }
    }
    mmap_enc_mat_clear(args->vtable, args->zero_enc[0]);
    fclose(fp);

    (void) snprintf(fname, fnamelen, "%s/%ld.one", args->dir, args->idx);
    fp = fopen(fname, "w+b");
    if (fp == NULL) {
        fprintf(stderr, "Unable to write '%s'\n", fname);
        goto done;
    }
    for (long i = 0; i < args->nrows; ++i) {
        for (long j = 0; j < args->ncols; ++j) {
            args->vtable->enc->fwrite(args->one_enc[0]->m[i][j], fp);
        }
    }
    mmap_enc_mat_clear(args->vtable, args->one_enc[0]);
    fclose(fp);

done:
    end = current_time();
    if (args->verbose)
        (void) fprintf(stderr, "  Encoding %ld elements: %f\n",
                       2 * args->nrows * args->ncols, end - args->start);

    free(args->zero_enc);
    free(args->one_enc);
    free(args);

    return NULL;
}

void *
thpool_write_element(void *vargs)
{
    FILE *fp;
    char fname[1024];
    int fnamelen = 1024;
    struct write_element_s *args = (struct write_element_s *) vargs;

    (void) snprintf(fname, fnamelen, "%s/%s", args->dir, args->name);
    fp = fopen(fname, "w+b");
    clt_vtable.enc->fwrite(args->elem, fp);
    fclose(fp);
    return NULL;
}
