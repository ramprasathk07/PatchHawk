def matrix_addition(mat1, mat2):
    """Add two matrices."""
    return [[mat1[i][j] + mat2[i][j] for j in range(len(mat1[0]))] for i in range(len(mat1))]