import hashlib
import bls
import utils


def test_verification_of_aggregate_signature():
    # generates and verfies a signature under the master key derived for contract
    # 0x64eB9cbc8AAc7723A7A94b178b7Ac4c18D7E6269
    # see ../evaluation/testnet-execution for the transscripts

    master_pk = (
        16185756129160603637125524807239031401829819645832054270709340132395400777397, 8519501919971397775891715048167089286600326398415030764834336433929153469650, 18597752777763136713734159587276505878060020022295659236248459536349704859281, 451510684427994150648572847494629298315616628846799867117722216880750483787
    )

    msg = 'test message'
    msg_hash = hashlib.sha3_256(msg.encode()).digest()

    # ids for the 3 correct nodes A, B, C (assigned durign registration)
    id_A, id_B, id_C = 3, 2, 1

    # group secret keys for the 3 correct nodes A, B and C
    gsk_A = (19063102076674778359749742475275688996157982969842615782345982391516317582432)
    gsk_B = (25409986690480885131491958594328734819629294462429970027081157236075400972958)
    gsk_C = (48802012483270245949082675044770005030925758437990233282811259804203609665090)

    sig_A = bls.sign(gsk_A, msg_hash)
    sig_B = bls.sign(gsk_B, msg_hash)
    sig_C = bls.sign(gsk_C, msg_hash)

    # three signature shares are sufficient to generate a signature which successfully verifies under the master pk
    sig = bls.aggregate([(id_A, sig_A), (id_B, sig_B), (id_C, sig_C)])
    assert bls.verify(master_pk, msg_hash, sig)

    # verify that the signature can also be verified in the smart contract
    contract = utils.deploy_contract('DKG')
    assert contract.verify_signature(master_pk, msg_hash, sig)
