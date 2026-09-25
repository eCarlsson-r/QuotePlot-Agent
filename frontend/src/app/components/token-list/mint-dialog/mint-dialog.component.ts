import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MaterialDesignModule } from '../../../modules/material-design/material-design.module';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ProgressSpinnerService } from '../../../services/progress-spinner.service';
import { ethers } from 'ethers';
 
export interface MintData {
  address: string;
  name: string;
  symbol: string;
  amount: string;
  contract: ethers.Contract;
  onMint: () => void;
}
 
@Component({
  selector: 'app-mint-dialog',
  standalone: true,
  imports: [
    FormsModule,
    MaterialDesignModule
  ],
  templateUrl: './mint-dialog.component.html',
  styleUrl: './mint-dialog.component.css'
})
export class MintDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<MintDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: MintData,
    private progressSpinnerService: ProgressSpinnerService
  ) {}

  get canSubmit(): boolean {
    const amount = String(this.data.amount ?? '').trim();
    return /^\d+$/.test(amount) && BigInt(amount) > 0n;
  }

  onMint() {
    if (!this.canSubmit) return;
    this.dialogRef.close();
    const amount = String(this.data.amount).trim();
    const promise = this.data.contract.mint(amount);
    this.progressSpinnerService.showSpinnerUntilExecuted(
      promise,
      this.data.onMint
    );
  }
 
  onCancel() {
    this.dialogRef.close();
  }
}
